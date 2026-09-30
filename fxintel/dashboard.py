#!/usr/bin/env python3
"""fxintel/dashboard.py - render a self-contained HTML intel dashboard.

Turns the fused brief (docs/brief.json + intel/latest.md + reports/alpha_search.json)
into a single shareable index.html. No JS deps, dark theme, mobile-friendly.
This is the storefront that makes the paid x402 API legible to a buyer.
"""
import os, json, html, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs"); os.makedirs(DOCS, exist_ok=True)


def jload(p, d=None):
    try: return json.load(open(os.path.join(ROOT, p)))
    except Exception: return d if d is not None else {}


def render():
    b = jload("docs/brief.json", {})
    alpha = jload("reports/alpha_search.json", {})
    sweep = jload("reports/xau_sweep.json", {})
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows = []
    for a in b.get("actionable", [])[:12]:
        rows.append(f'<li><span class="sc">{a.get("score","?")}</span>'
                    f'<a href="{html.escape(a.get("url","#"))}" target="_blank">{html.escape(a.get("title",""))}</a></li>')
    oos = alpha.get("D_mom20", {}).get("oos", {}) if isinstance(alpha, dict) else {}
    fam_tbl = ""
    if isinstance(alpha, dict):
        for name, v in alpha.items():
            o = v.get("oos", {})
            fam_tbl += (f"<tr><td>{html.escape(name)}</td><td>{o.get('trades','-')}</td>"
                        f"<td>{o.get('win_pct','-')}%</td><td class='{'pos' if o.get('ret_pct',0)>0 else 'neg'}'>"
                        f"{o.get('ret_pct','-')}%</td><td>{o.get('pf','-')}</td><td>{o.get('sharpe','-')}</td></tr>")
    htmlout = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Conway Intelligence — Actionable Brief</title>
<style>
:root{{--bg:#0b0f14;--fg:#e6edf3;--mut:#8b949e;--card:#111820;--acc:#3fb950;--neg:#f85149;--gold:#d29922}}
*{{box-sizing:border-box}}body{{margin:0;font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg)}}
.wrap{{max-width:860px;margin:0 auto;padding:28px 18px 60px}}
h1{{font-size:22px;margin:0 0 4px}}.sub{{color:var(--mut);font-size:13px;margin-bottom:22px}}
.card{{background:var(--card);border:1px solid #21262d;border-radius:12px;padding:16px 18px;margin:14px 0}}
h2{{font-size:15px;color:var(--gold);margin:0 0 12px;letter-spacing:.3px;text-transform:uppercase}}
ul{{list-style:none;padding:0;margin:0}}li{{padding:8px 0;border-bottom:1px solid #1b2129}}
li:last-child{{border:0}}a{{color:var(--fg);text-decoration:none}}a:hover{{color:var(--acc)}}
.sc{{display:inline-block;min-width:22px;text-align:center;background:#1f6feb;border-radius:6px;font-size:12px;padding:1px 6px;margin-right:9px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{text-align:right;padding:7px 6px;border-bottom:1px solid #1b2129}}th:first-child,td:first-child{{text-align:left}}
th{{color:var(--mut);font-weight:500}}.pos{{color:var(--acc)}}.neg{{color:var(--neg)}}
.badge{{display:inline-block;background:#238636;color:#fff;border-radius:20px;font-size:11px;padding:2px 10px;margin-left:8px}}
.paid{{font-size:13px;color:var(--mut)}}.paid code{{background:#161b22;padding:2px 6px;border-radius:5px;color:var(--gold)}}
</style></head><body><div class="wrap">
<h1>Conway Intelligence<span class="badge">LIVE</span></h1>
<div class="sub">Actionable market brief · generated {now} · 8 free feeds + risk-governed market view</div>

<div class="card"><h2>Top actionable drivers</h2><ul>{''.join(rows) or '<li>collecting…</li>'}</ul></div>

<div class="card"><h2>Strategy research — out-of-sample truth</h2>
<table><tr><th>Family</th><th>Trades</th><th>Win</th><th>OOS ret</th><th>PF</th><th>Sharpe</th></tr>{fam_tbl}</table>
<p class="paid" style="margin-top:12px">Verdict: no simple-rule edge on 210,384 real M5 gold bars (2024-09→2026-09).
<b>Capital preserved, zero at risk.</b> Methodology open-sourced in repo.</p></div>

<div class="card"><h2>Paid API (x402 · USDC on Base)</h2>
<p class="paid">Free: <code>GET /brief</code> · <code>GET /news</code><br>
Paid: <code>GET /intel</code> (0.02 USDC) · <code>GET /signal</code> (0.005 USDC)<br>
Pay to <code>0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D</code></p></div>
</div></body></html>"""
    open(os.path.join(DOCS, "index.html"), "w").write(htmlout)
    return len(rows)


if __name__ == "__main__":
    print("dashboard rows:", render(), "-> docs/index.html")
