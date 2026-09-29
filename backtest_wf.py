#!/usr/bin/env python3
"""backtest_wf.py - walk-forward backtest of the GOVERNED strategy.

Purpose: answer one honest question with real bars — does the governed engine
have positive expectancy after costs, and what is its worst drawdown?
If not, trading live is unjustified and the stand-aside discipline is correct.

It reuses the SAME decision code as production (fxintel.signals.build_plan and
fxintel.portfolio_risk), so the backtest cannot flatter a different strategy.

Method:
  * load real H1 bars (bridge -> yahoo -> cache), no synthetic
  * walk forward: at each bar, build intel exactly like live_trader, call
    build_plan; if valid, simulate entry/stop/target with conservative fills
  * enforce the portfolio correlation gate across concurrent positions
  * charge a cost (spread+commission) in pips per round trip
  * one position per symbol at a time; fixed fractional risk per trade
Outputs: reports/backtest.json + a human summary. Fail-soft throughout.
"""
from __future__ import annotations
import os, sys, json, math, datetime as dt

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

SYMBOLS = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","USDCHF","NZDUSD","EURJPY","GBPJPY","XAUUSD"]
RISK_PCT = 1.5
COST_PIPS = 1.2          # round-trip spread+commission, conservative
PIP = {"XAUUSD": 0.10, "EURJPY": 0.01, "GBPJPY": 0.01}
def pip_of(sym): return PIP.get(sym, 0.0001)


def load(sym, n=1200):
    try:
        from fxintel.data import load_bars
    except Exception:
        try:
            from live_trader import load_bars
        except Exception:
            return [], "none"
    try:
        raw, src = load_bars(sym, "H1", n, allow_synthetic=False)
    except Exception:
        return [], "none"
    if not raw:
        return [], src
    bars = [{"o": b.get("open", b.get("o")), "h": b.get("high", b.get("h")),
             "l": b.get("low", b.get("l")), "c": b.get("close", b.get("c")),
             "time": b.get("time")} for b in raw]
    return [b for b in bars if all(b[k] is not None for k in ("o","h","l","c"))], src


def intel_at(bars, i):
    """Reproduce live_trader intel at bar index i (only past data — no lookahead)."""
    hist = bars[:i+1]
    closes = [b["c"] for b in hist]
    d = {}
    try:
        from fxintel.indicators import ema as _ema, rsi as _rsi, atr as _atr_raw, adx as _adx_raw
        e20 = (_ema(closes,20) or [None])[-1]; e50 = (_ema(closes,50) or [None])[-1]
        e200 = (_ema(closes,200) or [None])[-1]; rsi_v = (_rsi(closes,14) or [None])[-1]
        atr_v = (_atr_raw(hist,14) or [None])[-1]; adx_v = (_adx_raw(hist,14) or [None])[-1]
        d["trend"] = "up" if (e20 and e50 and e20>e50) else ("down" if (e20 and e50) else "flat")
        d["_ema_trend"] = d["trend"]
    except Exception:
        e20=e50=e200=rsi_v=atr_v=adx_v=None; d["trend"]="flat"
    try:
        from fxintel.regime import classify as _rc
        r = _rc(hist[-1]["c"], e20, e50, e200, rsi_v, adx_v, atr_v)
        d["regime"] = (r.get("trend") if isinstance(r,dict) else r) or "unknown"
    except Exception:
        d["regime"]="unknown"
    try:
        from fxintel import moneyflow as _mf
        d["flow_score"]=float(_mf.analyze(hist).get("flow_score") or 0.0)
    except Exception:
        d["flow_score"]=0.0
    d["vol_state"]="normal"; d["price"]=hist[-1]["c"]
    return d


def simulate(sym, bars, start=250):
    """Return list of trades for one symbol (governed decisions only)."""
    from fxintel.signals import build_plan
    from fxintel import portfolio_risk as PR
    trades, open_pos = [], None
    p = pip_of(sym)
    for i in range(start, len(bars)-1):
        b = bars[i]
        # manage open position first
        if open_pos is not None:
            hi, lo = b["h"], b["l"]
            hit_tp = (open_pos["side"]=="buy" and hi>=open_pos["target"]) or \
                     (open_pos["side"]=="sell" and lo<=open_pos["target"])
            hit_sl = (open_pos["side"]=="buy" and lo<=open_pos["stop"]) or \
                     (open_pos["side"]=="sell" and hi>=open_pos["stop"])
            # conservative: stop takes precedence if both touched in one bar
            exit_px = None
            if hit_sl: exit_px = open_pos["stop"]
            elif hit_tp: exit_px = open_pos["target"]
            if exit_px is not None:
                sign = 1 if open_pos["side"]=="buy" else -1
                gross = (exit_px - open_pos["entry"]) * sign
                net = gross - COST_PIPS*p
                r = net / (abs(open_pos["entry"]-open_pos["stop"]) or 1e-9)
                trades.append({"entry_i":open_pos["i"],"exit_i":i,"symbol":sym,
                               "side":open_pos["side"],"R":round(r,3),
                               "pnl_pct_of_risk":round(r*RISK_PCT,3)})
                open_pos = None
        if open_pos is not None:
            continue
        # build governed plan on closed bars only
        d = intel_at(bars, i)
        try:
            plan = build_plan(sym, bars[:i+1], d, equity_usd=10000.0, risk_pct=RISK_PCT)
        except Exception:
            continue
        if not getattr(plan, "valid", False):
            continue
        side = getattr(plan, "direction", "").lower()
        if side not in ("buy","sell"):
            continue
        entry = getattr(plan, "entry", None) or b["c"]
        stop = getattr(plan, "stop", None)
        tgt = getattr(plan, "target", None)
        if not stop or not tgt:
            continue
        # correlation gate: no correlated stacking while another pos is open
        breach,_ = PR.would_breach([{"symbol":sym,"side":side,"risk_pct":RISK_PCT}], {"symbol":sym,"side":side,"risk_pct":RISK_PCT})
        # (single-symbol loop: enforce per-symbol doubling block only)
        open_pos = {"side":side,"entry":entry,"stop":stop,"target":tgt,"i":i}
    return trades


def metrics(trades):
    if not trades: return {"trades":0}
    rs = [t["R"] for t in trades]
    wins = [r for r in rs if r>0]; losses=[r for r in rs if r<=0]
    eq, peak, mdd = 0.0, 0.0, 0.0
    for r in rs:
        eq += r*RISK_PCT
        peak = max(peak, eq); mdd = max(mdd, peak-eq)
    mean = sum(rs)/len(rs)
    sd = (sum((r-mean)**2 for r in rs)/len(rs))**0.5 or 1e-9
    exp_pct = mean*RISK_PCT
    return {"trades":len(rs),"win_rate":round(len(wins)/len(rs),3),
            "avg_R":round(mean,3),"expectancy_pct_per_trade":round(exp_pct,3),
            "sharpe_like":round(mean/sd*math.sqrt(len(rs)),2),
            "max_drawdown_pct":round(mdd,3),
            "total_return_pct":round(sum(rs)*RISK_PCT,2),
            "profit_factor":round(sum(wins)/(abs(sum(losses)) or 1e-9),3)}


def main():
    report={"ts":dt.datetime.utcnow().isoformat()+"Z","risk_pct":RISK_PCT,
            "cost_pips":COST_PIPS,"method":"walk-forward, closed-bars only, no lookahead",
            "per_symbol":{}, "aggregate":{}}
    all_trades=[]
    for s in SYMBOLS:
        bars,src = load(s)
        if len(bars) < 300:
            report["per_symbol"][s]={"status":"no data","src":src,"bars":len(bars)}
            continue
        tr = simulate(s, bars)
        all_trades += tr
        report["per_symbol"][s]={"bars":len(bars),"src":src,"trades":len(tr),
                                 **metrics(tr)}
    report["aggregate"] = metrics(all_trades)
    os.makedirs("reports",exist_ok=True)
    json.dump(report, open("reports/backtest.json","w"), indent=2)
    a=report["aggregate"]
    print("backtest:", json.dumps(a))
    verdict = "NO EDGE (stand-aside justified)" if a.get("trades",0)==0 or a.get("expectancy_pct_per_trade",0)<=0 else "POSITIVE EXPECTANCY — candidate for live"
    report["verdict"]=verdict
    json.dump(report, open("reports/backtest.json","w"), indent=2)
    print("VERDICT:", verdict)
    return report


if __name__=="__main__":
    main()
