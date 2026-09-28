#!/usr/bin/env python3
"""Daily actionable market brief: fuses news_digest + risk-governed signals.
Honest, human-readable, self-contained. Serves as free top-of-funnel."""
import os, json, time, datetime

HERE=os.path.dirname(os.path.abspath(__file__))

def _read(path, default=""):
    try: return open(os.path.join(HERE,path)).read()
    except Exception: return default

def _news_items(limit=8):
    md=_read("reports/news_digest.md")
    out=[]
    for line in md.splitlines():
        if "[ACTIONABLE]" in line:
            out.append(line.strip("- ").strip())
        if len(out)>=limit: break
    return out

def _plans():
    try:
        from fxintel.signals import build_plan
        from intel_service import intel, SYMBOLS
    except Exception as e:
        return [], f"signal engine unavailable: {e}"
    valid=[]; scanned=0
    for sym in SYMBOLS:
        try: d=intel(sym,"1h")
        except Exception: continue
        scanned+=1
        p=build_plan(sym, d.get("_bars") or [], d, equity_usd=10000.0, risk_pct=1.0)
        if p.valid: valid.append(p)
    return valid, f"scanned {scanned} symbols"

def render(equity=10000.0):
    now=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    plans, note = _plans()
    news = _news_items()
    L=[]
    L.append(f"# Daily Market Brief — {now}")
    L.append("")
    L.append("_Risk-governed. Honest. No trade is better than a bad trade._")
    L.append("")
    L.append("## 1. Actionable headlines")
    if news:
        for n in news: L.append(f"- {n}")
    else:
        L.append("- No high-conviction headlines in the current feed window.")
    L.append("")
    L.append(f"## 2. Governed trade plans  (equity ${equity:,.0f}, risk ≤ 1%/trade)")
    if plans:
        L.append("")
        L.append("| Symbol | Side | Entry | Stop | Target | R:R | Size | Risk $ |")
        L.append("|---|---|---|---|---|---|---|---|")
        for p in plans:
            L.append(f"| {p.symbol} | {p.side} | {p.entry} | {p.stop} | {p.target} "
                     f"| {p.rr} | {p.size_lots} | {p.risk_usd} |")
    else:
        L.append("")
        L.append(f"**Standing aside.** {note}. No symbol has aligned trend + money-flow "
                 "conviction, so the rules produce no trade. Capital preserved by default.")
    L.append("")
    L.append("## 3. Rules in force")
    L.append("- Max 1% equity risk per trade; sizing FLOORed (never breaches cap).")
    L.append("- Mandatory stop-loss at 1.5×ATR; target ≥ 1.5R.")
    L.append("- No martingale, no averaging into losses, size capped.")
    L.append("- Trades only on aligned trend + flow; otherwise FLAT.")
    L.append("")
    L.append("_Paper/analysis only until a broker (MT5) bridge exists._")
    md="\n".join(L)
    os.makedirs(os.path.join(HERE,"reports"),exist_ok=True)
    open(os.path.join(HERE,"reports","daily_brief.md"),"w").write(md)
    return md

if __name__=="__main__":
    print(render())
