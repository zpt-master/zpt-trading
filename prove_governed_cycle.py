#!/usr/bin/env python3
"""PROOF: end-to-end risk-governed decision on REAL bars.

Shows, per symbol: real bars -> indicators -> regime -> moneyflow ->
signal engine (build_plan) -> EDGE GATE (OOS expectancy) -> final decision.
Nothing here places an order. It demonstrates the hard chain:
  no real bars        -> SKIP
  no trend+flow align -> STAND ASIDE
  no OOS edge         -> BLOCK
  else                -> would-place (governed, risk<=1.5%, mandatory stop)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fxintel.bars import load as load_bars, is_real
from fxintel.edge import best as edge_best
from fxintel.signals import build_plan

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD"]

def norm(raw):
    return [{"o": b.get("open", b.get("o")), "h": b.get("high", b.get("h")),
             "l": b.get("low", b.get("l")), "c": b.get("close", b.get("c")),
             "time": b.get("time")} for b in raw]

def run():
    from fxintel.indicators import ema, rsi, atr, adx
    for sym in SYMBOLS:
        raw, src = load_bars(sym, "H1", 400, allow_synthetic=False)
        if not raw or not is_real(src):
            print("%-7s SKIP  no real bars (src=%s)" % (sym, src)); continue
        bars = norm(raw); closes = [b["c"] for b in bars]
        e20 = (ema(closes, 20) or [None])[-1]
        e50 = (ema(closes, 50) or [None])[-1]
        e200 = (ema(closes, 200) or [None])[-1]
        rsi_v = (rsi(closes, 14) or [None])[-1]
        atr_v = (atr(bars, 14) or [None])[-1]
        adx_v = (adx(bars, 14) or [None])[-1]
        trend = "up" if (e20 and e50 and e20 > e50) else ("down" if (e20 and e50) else "flat")

        regime = "unknown"
        try:
            from fxintel.regime import classify
            _rg = classify(bars[-1]["c"], e20, e50, e200, rsi_v, adx_v, atr_v)
            regime = (_rg.get("trend") if isinstance(_rg, dict) else _rg) or "unknown"
        except Exception:
            pass

        flow = 0.0
        try:
            from fxintel import moneyflow as mf
            flow = float(mf.analyze(bars).get("flow_score") or 0.0)
        except Exception:
            pass

        intel = {"trend": trend, "regime": regime, "flow_score": flow,
                 "vol_state": "normal", "price": bars[-1]["c"]}
        plan = build_plan(sym, bars, intel, equity_usd=10000.0, risk_pct=1.5)

        er = edge_best(sym, bars, min_expectancy_R=0.03)
        print("%-7s bars=%d src=%s trend=%s regime=%s flow=%+.0f" %
              (sym, len(bars), src, trend, regime, flow))
        print("        plan: %-7s valid=%s  %s" %
              (getattr(plan, "side", "?"), getattr(plan, "valid", False),
               getattr(plan, "rationale", "")[:70]))
        print("        edge: %-8s %s trades=%d exp=%+.3fR pf=%.2f" %
              (er.strategy, "APPROVED" if er.approved else "REJECT",
               er.trades, er.expectancy_R, er.profit_factor))

        if not getattr(plan, "valid", False):
            print("        => DECISION: STAND ASIDE (no aligned conviction)"); continue
        if not er.approved:
            print("        => DECISION: BLOCKED (no out-of-sample edge)"); continue
        print("        => DECISION: WOULD PLACE %s risk<=%.1f%% stop=%s tgt=%s lots=%.2f" %
              (plan.side, plan.risk_pct, plan.stop, plan.target, plan.size_lots))

if __name__ == "__main__":
    run()
