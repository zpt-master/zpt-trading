#!/usr/bin/env python3
"""
signal_engine.py - Risk-governed trade plan generator.

Turns Conway Intelligence market state (trend/regime/flow) into CONCRETE,
rule-bound trade PLANS. Governance is non-negotiable:
  - risk per trade <= 1% of equity (configurable, capped at 2%)
  - every plan MUST carry a stop-loss
  - leverage limited; no martingale, no averaging into losers
  - position size derived from risk, not from conviction
Plans are journaled to reports/trade_plans.jsonl for audit.
If MT5 is present, plans can be executed at minimum size; otherwise plans are
recorded as PAPER (honest: no live fills without MT5).
"""
import os, json, time, math
from datetime import datetime, timezone

RISK_PCT      = 0.01     # 1% equity risk per trade (hard cap 2%)
MAX_RISK_PCT  = 0.02
MIN_RR        = 1.5      # only take setups with reward:risk >= 1.5
EQUITY_USD    = float(os.environ.get("TRADING_EQUITY_USD", "1000"))
JOURNAL       = os.path.join("reports", "trade_plans.jsonl")

def _clamp_risk(pct):
    return max(0.001, min(float(pct), MAX_RISK_PCT))

def _plan(symbol, side, price, atr, equity=EQUITY_USD, risk_pct=RISK_PCT):
    """Build a single risk-governed plan. Stop distance = 1.5*ATR (volatility-scaled)."""
    risk_pct = _clamp_risk(risk_pct)
    if not price or not atr or price<=0 or atr<=0:
        return None
    stop_dist = 1.5*atr
    if side=="LONG":
        stop = price-stop_dist
        target = price + MIN_RR*stop_dist
    else:
        stop = price+stop_dist
        target = price - MIN_RR*stop_dist
    risk_usd = equity*risk_pct
    # units = risk_usd / stop_dist  (position sizing from risk, NOT conviction)
    units = risk_usd/stop_dist if stop_dist>0 else 0
    notional = units*price
    leverage = notional/equity if equity>0 else 0
    if leverage > 5:            # hard leverage ceiling
        units = (5*equity)/price; notional = units*price; leverage = 5.0
    rr = abs(target-price)/abs(price-stop) if abs(price-stop)>0 else 0
    return {
        "symbol":symbol,"side":side,"entry":round(price,5),
        "stop_loss":round(stop,5),"take_profit":round(target,5),
        "risk_pct":round(risk_pct,4),"risk_usd":round(risk_usd,2),
        "units":round(units,4),"notional":round(notional,2),
        "leverage":round(leverage,2),"r_multiple_target":round(rr,2),
        "stop_basis":"1.5*ATR","mandate":"stop-loss + <=2% risk + RR>=1.5",
    }

def plan_from_state(symbol, d, equity=EQUITY_USD, risk_pct=RISK_PCT):
    """d = intel dict from intel_service/intel(). Decide side from trend/flow/regime."""
    price = d.get("price") or (d.get("last") or {})
    if isinstance(price, dict): price = price.get("close") or price.get("c")
    atr = d.get("atr") or d.get("atr14")
    trend = str(d.get("trend","")).upper()
    flow  = d.get("flow_regime") or d.get("regime") or ""
    score = d.get("flow_score", 0) or 0
    try: score=float(score)
    except Exception: score=0
    side=None
    if ("UP" in trend or "BULL" in trend) and ("ACCUM" in flow.upper() or score>=15): side="LONG"
    elif ("DOWN" in trend or "BEAR" in trend) and ("DISTRIB" in flow.upper() or score<=-15): side="SHORT"
    if not side: return None
    return _plan(symbol, side, float(price or 0), float(atr or 0), equity, risk_pct)

def journal(plan):
    os.makedirs("reports", exist_ok=True)
    rec = {"ts":datetime.now(timezone.utc).isoformat(), "mode":("MT5" if _mt5_available() else "PAPER"), **plan}
    with open(JOURNAL,"a") as f: f.write(json.dumps(rec)+"\n")
    return rec

def _mt5_available():
    try:
        import MetaTrader5  # noqa
        return True
    except Exception:
        return False

def generate(symbols, intel_fn, equity=EQUITY_USD, risk_pct=RISK_PCT):
    plans=[]
    for s in symbols:
        try:
            d=intel_fn(s,"1h")
        except Exception:
            continue
        p=plan_from_state(s, d or {}, equity, risk_pct)
        if p:
            journal(p); plans.append(p)
    return plans

if __name__=="__main__":
    import sys
    if len(sys.argv)>1 and sys.argv[1]=="selftest":
        # deterministic self-test: no network, proves governance math
        d={"price":1.1000,"atr":0.0010,"trend":"UPTREND","flow_regime":"ACCUMULATION","flow_score":40}
        p=plan_from_state("EURUSD", d)
        assert p and p["stop_loss"]<p["entry"] and p["risk_pct"]<=0.02 and p["r_multiple_target"]>=1.5, p
        rec=journal(p)
        print("SELFTEST OK:", json.dumps(p))
    else:
        print("usage: python3 -m fxintel.signal_engine selftest")
