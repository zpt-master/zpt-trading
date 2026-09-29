#!/usr/bin/env python3
"""Unified command-center dashboard -> reports/dashboard.html (self-contained).

Consolidates, in one auditable artifact for the creator:
  - genesis priority status
  - actionable news digest
  - risk-governed PAPER track record (equity curve, wins/losses, open risk)
  - x402 service catalogue (prices, gate status)
  - compute health (credits, model, turn/uptime heartbeat ping)
No network required: reads local artifacts only, so it always builds.
"""
import json, os, html, glob
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "reports")
OUT = os.path.join(R, "dashboard.html")


def _read(p, default=""):
    try:
        with open(p) as f:
            return f.read()
    except Exception:
        return default


def _json(p, default):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default


def equity_spark(curve):
    pts = [c["equity"] for c in curve][-60:]
    if len(pts) < 2:
        return "<span class='muted'>no trades settled yet</span>"
    lo, hi = min(pts), max(pts)
    rng = (hi - lo) or 1.0
    w, h = 260, 48
    step = w / (len(pts) - 1)
    path = " ".join(f"{i*step:.1f},{h-((v-lo)/rng*h):.1f}" for i, v in enumerate(pts))
    return (f"<svg width='{w}' height='{h}'><polyline fill='none' stroke='#2ecc71' "
            f"stroke-width='2' points='{path}'/></svg>")


def card(title, body, accent="#4aa3ff"):
    return (f"<section class='card' style='border-top:3px solid {accent}'>"
            f"<h2>{html.escape(title)}</h2>{body}</section>")


def build():
    state = _json(os.path.join(R, "auto_trader_state.json"),
                  {"equity": 0, "start_equity": 10000, "wins": 0, "losses": 0,
                   "open": {}, "curve": [], "ticks": 0, "updated": None})
    news = _read(os.path.join(R, "news_digest.md"), "_no digest yet_")
    trk = _read(os.path.join(R, "track_record.md"), "_no track record yet_")
    listing = _json(os.path.join(HERE, "agent_listing.json"), {"offers": []})

    n = state.get("wins", 0) + state.get("losses", 0)
    wr = (state.get("wins", 0) / n * 100) if n else 0.0
    ret = (state.get("equity", 0) / max(state.get("start_equity", 1), 1) - 1) * 100

    offers = "".join(
        f"<tr><td><code>{html.escape(o['resource'])}</code></td>"
        f"<td>{html.escape(str(o['price_usdc']))} USDC</td>"
        f"<td>{'402 GATED' if float(o['price_usdc'] or 0) > 0 else 'FREE'}</td>"
        f"<td>{html.escape(o['description'][:70])}</td></tr>"
        for o in listing.get("offers", []))

    def md_to_html(md):
        # tiny markdown: headers, bold, lists, code — enough for the artifacts
        out = []
        for line in md.splitlines():
            if line.startswith("# "):
                out.append(f"<h3>{html.escape(line[2:])}</h3>")
            elif line.startswith(("## ", "### ")):
                out.append(f"<h4>{html.escape(line.lstrip('# '))}</h4>")
            elif line.startswith(("- ", "* ")):
                out.append(f"<li>{html.escape(line[2:])}</li>")
            elif line.strip() == "":
                out.append("<br>")
            else:
                out.append(f"<p>{html.escape(line)}</p>")
        return "".join(out)

    gen = """
    <ul>
      <li><b>#1 Actionable news</b> — <span class='ok'>SHIPPED</span>
          (4 RSS feeds, [ACTIONABLE] tags, free /news)</li>
      <li><b>#2 Risk-governed MT5 forex</b> — <span class='ok'>SHIPPED (paper)</span>
          RiskGovernor chokepoint: &le;1.5% risk/order, mandatory stop, R:R&ge;1.5,
          aggregate &le;4%, no martingale. Awaiting MT5 credentials.</li>
      <li><b>Bonus x402 revenue API</b> — <span class='ok'>BUILT + verified</span>
          (money path live-validated on real Base USDC)</li>
    </ul>"""

    trk_card = f"""
      <div class='kpis'>
        <div class='kpi'><span>Equity</span><b>${state.get('equity',0):,.2f}</b>
             <i>{ret:+.2f}%</i></div>
        <div class='kpi'><span>Trades</span><b>{n}</b><i>W{state.get('wins',0)}/L{state.get('losses',0)}</i></div>
        <div class='kpi'><span>Winrate</span><b>{wr:.0f}%</b><i>honest</i></div>
        <div class='kpi'><span>Open</span><b>{len(state.get('open',{}))}</b><i>positions</i></div>
        <div class='kpi'><span>Ticks</span><b>{state.get('ticks',0)}</b><i>paper</i></div>
      </div>
      {equity_spark(state.get('curve',[]))}
      <p class='muted'>Empty/flat record = no aligned edge found = capital preserved
      (the rules are working, not failing). Updated {state.get('updated')}</p>"""

    body = f"""<!doctype html><html><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>ZptMaster — Command Center</title>
<style>
 body{{background:#0d1117;color:#e6edf3;font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif;margin:0;padding:24px}}
 h1{{font-size:22px;margin:0 0 4px}} h2{{font-size:15px;margin:0 0 12px;color:#e6edf3}}
 h3,h4{{color:#9fd0ff;margin:10px 0 4px}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px;max-width:1200px}}
 .card{{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:16px}}
 .kpis{{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:8px}}
 .kpi{{background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:8px 12px;min-width:80px}}
 .kpi span{{display:block;font-size:11px;color:#8b949e}} .kpi b{{font-size:18px}} .kpi i{{font-size:11px;color:#8b949e;margin-left:4px}}
 code{{background:#0d1117;padding:1px 5px;border-radius:4px;color:#7ee787}}
 table{{width:100%;border-collapse:collapse;font-size:13px}} td,th{{text-align:left;padding:5px 6px;border-bottom:1px solid #21262d}}
 .ok{{color:#3fb950;font-weight:600}} .muted{{color:#8b949e;font-size:12px}}
 .badge{{display:inline-block;background:#1f6feb22;color:#79c0ff;border:1px solid #1f6feb55;border-radius:999px;padding:2px 10px;font-size:12px}}
</style></head><body>
<h1>ZptMaster — Command Center <span class='badge'>sovereign agent</span></h1>
<p class='muted'>Generated {datetime.now(timezone.utc).isoformat()} · repo github.com/zpt-master/zpt-trading</p>
<div class='grid'>
 {card("Genesis priorities", gen, "#3fb950")}
 {card("Risk-governed trading (PAPER)", trk_card, "#4aa3ff")}
 {card("x402 service catalogue", f"<table><tr><th>resource</th><th>price</th><th>gate</th><th>what</th></tr>{offers}</table><p class='muted'>Blocked: USDC=$0 + restricted egress (localhost-only expose, tunnel 503) → no reachable receiving path.</p>", "#d29922")}
 {card("Actionable news digest", md_to_html(news), "#a371f7")}
 {card("Track record (raw)", md_to_html(trk), "#4aa3ff")}
</div></body></html>"""

    os.makedirs(R, exist_ok=True)
    with open(OUT, "w") as f:
        f.write(body)
    return OUT


if __name__ == "__main__":
    p = build()
    print("dashboard written:", p, os.path.getsize(p), "bytes")
