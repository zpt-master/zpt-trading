"""
signals.py - Risk-governed signal engine (genesis task #2).

Turns the intel feed (trend/regime/vol/flow) into CONCRETE, RULE-BOUND trade
plans. Non-negotiable risk rules (from the genesis prompt):
  * risk <= 1-2% of equity per trade
  * EVERY plan carries a stop-loss
  * no martingale, no averaging into losers, no leveraged over-size
  * capital preservation > short-term profit

The engine does NOT decide to be right about the market. It decides how much
can be lost, where the stop goes, and what a disciplined target is. Output is a
plain trade ticket that MT5 (or a paper journal) can execute.
"""
from dataclasses import dataclass, asdict
from typing import Optional

# pip value model: for USD-quoted major FX, 1 standard lot (100k) ~ $10/pip.
# For XAUUSD, 1 lot (100 oz) ~ $1 per $0.01 move = $100 per $1 move.
PIP = {"EURUSD":0.0001,"GBPUSD":0.0001,"USDJPY":0.01,"AUDUSD":0.0001,
       "USDCAD":0.0001,"NZDUSD":0.0001,"XAUUSD":0.10}

@dataclass
class TradePlan:
    symbol: str
    side: str              # LONG / SHORT / FLAT
    entry: float
    stop: float
    target: float
    risk_pct: float
    rr: float
    size_lots: float
    risk_usd: float
    rationale: str
    confidence: str
    valid: bool

def _pip(sym): return PIP.get(sym.upper(), 0.0001)

def _atr(bars, n=14):
    """Average true range (dependency-free)."""
    if len(bars) < 2: return None
    get = lambda b,k: float(b[k] if isinstance(b,dict) else getattr(b,k))
    trs=[]
    for i in range(1,len(bars)):
        h=get(bars[i],"h"); l=get(bars[i],"l"); pc=get(bars[i-1],"c")
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    if not trs: return None
    k=min(n,len(trs))
    return sum(trs[-k:])/k

def build_plan(symbol, bars, d, equity_usd=10000.0, risk_pct=1.0,
               min_rr=1.5, stop_atr=1.5):
    """
    d = intel dict for symbol (has: trend, regime, vol_state, flow_score, price).
    Returns a TradePlan. FLAT/invalid when the rules don't line up.
    """
    sym=symbol.upper()
    side="FLAT"; reason=[]; valid=False
    entry=float(d.get("price") or 0) or (float(bars[-1]["c"]) if bars else 0)
    trend=(d.get("trend") or "").upper()
    _reg = d.get("regime")
    if isinstance(_reg, dict):
        _reg = _reg.get("trend") or ""
    regime=(_reg or "").upper()
    flow=float(d.get("flow_score") or 0)
    vol=(d.get("vol_state") or "").upper()

    # ---- Rule: only trade WITH aligned trend + flow conviction ----
    if ("UP" in trend or "BULL" in trend) and flow >= 15 and "DISTRIB" not in regime:
        side="LONG"
    elif ("DOWN" in trend or "BEAR" in trend) and flow <= -15 and "ACCUM" not in regime:
        side="SHORT"

    if side=="FLAT":
        return TradePlan(sym,"FLAT",entry,0,0,risk_pct,0,0,0,
                         "no aligned trend+flow conviction -> stand aside",
                         "none",False)

    atr=_atr(bars) or (entry*0.005)
    dist=stop_atr*atr
    if side=="LONG":
        stop=entry-dist; target=entry+dist*max(min_rr,1.5)
    else:
        stop=entry+dist; target=entry-dist*max(min_rr,1.5)

    # ---- Rule: position size so that (entry-stop) loss == risk_pct of equity ----
    risk_usd=equity_usd*risk_pct/100.0
    per_unit_price=abs(entry-stop)
    if per_unit_price<=0:
        return TradePlan(sym,"FLAT",entry,0,0,risk_pct,0,0,0,"degenerate stop",'none',False)
    # convert price distance to pips, then lots: loss_per_lot = pips * $10 /pip (FX)
    pips=per_unit_price/_pip(sym)
    pip_val_per_lot=100.0 if sym=="XAUUSD" else 10.0
    loss_per_lot=pips*pip_val_per_lot
    import math
    # FLOOR (never round up): rounding up would breach the 1% risk cap.
    raw=risk_usd/loss_per_lot if loss_per_lot>0 else 0
    size=math.floor(raw*100)/100.0
    # ---- Rule: hard cap, never over-size (no leverage abuse) ----
    size=min(size, 5.0)
    rr=round(abs(target-entry)/per_unit_price,2) if per_unit_price else 0

    reason.append(f"trend={trend}")
    reason.append(f"flow={flow:+.0f}")
    reason.append(f"regime={regime or 'n/a'}")
    if vol: reason.append(f"vol={vol}")
    reason.append(f"ATR={atr:.5g} stop={stop_atr}xATR RR={rr}")

    realized=size*loss_per_lot
    if realized>risk_usd and loss_per_lot>0:   # hard guarantee: never exceed risk budget
        size=math.floor((risk_usd/loss_per_lot)*100)/100.0
        realized=size*loss_per_lot
    valid = size>0 and rr>=min_rr and risk_pct<=2.0 and realized<=risk_usd+0.011
    conf = "high" if abs(flow)>=35 and rr>=2 else ("medium" if abs(flow)>=20 else "low")
    return TradePlan(sym, side, round(entry,5), round(stop,5), round(target,5),
                     risk_pct, rr, size, round(realized,2),
                     "; ".join(reason), conf, valid)

def plan_to_dict(p): return asdict(p)
