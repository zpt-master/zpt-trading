#!/usr/bin/env python3
"""Scan all symbols -> risk-governed trade plans -> journal. Genesis task #2."""
import sys
try:
    from fxintel.signals import build_plan
    from fxintel.journal import log_plan, daily_summary
    from intel_service import intel, SYMBOLS
except Exception as e:
    print("import error:",e); sys.exit(1)
equity=float(sys.argv[1]) if len(sys.argv)>1 else 10000.0
rows=[]
for sym in SYMBOLS:
    try:
        d=intel(sym,"1h")
    except Exception as e:
        continue
    bars=d.get("_bars") or []
    p=build_plan(sym, bars, d, equity_usd=equity, risk_pct=1.0)
    log_plan(p)
    rows.append(p)
valid=[r for r in rows if r.valid]
print(f"scanned={len(rows)} valid_plans={len(valid)}")
for r in valid:
    print(f"  {r.side:5} {r.symbol:7} entry={r.entry} stop={r.stop} target={r.target} "
          f"RR={r.rr} size={r.size_lots} risk=${r.risk_usd} [{r.confidence}]")
print("journal:",daily_summary())
