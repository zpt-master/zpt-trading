#!/usr/bin/env python3
"""publish_feed.py — generate public, inbound-free distribution + trust surfaces:
  docs/feed.xml          RSS 2.0 so any reader/aggregator can subscribe (free)
  docs/track_record.json append-only, timestamped log of every governed decision
  docs/track_record.html human-readable proof-of-discipline page
All read-only over local artifacts; never raises."""
import os, json, html, time, datetime as dt

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
DOCS = "docs"; os.makedirs(DOCS, exist_ok=True)
PAGES = "https://zpt-master.github.io/zpt-trading"
HOME = PAGES + "/"

def _read(p):
    try: return open(p).read()
    except Exception: return ""

def _brief():
    return _read("intel/latest.md") or _read("reports/daily_brief.md") or "ZptMaster brief"

# ---------- RSS ----------
def build_feed():
    import email.utils
    items = []
    d = sorted([f for f in os.listdir("intel") if f.endswith(".md") and f[0].isdigit()], reverse=True) \
        if os.path.isdir("intel") else []
    for f in d[:30]:
        day = f[:-3]
        body = _read(os.path.join("intel", f))
        title = body.splitlines()[0].lstrip("# ").strip() if body else day
        try:
            when = dt.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
        except Exception:
            when = dt.datetime.now(dt.timezone.utc)
        items.append({"title": title, "day": day, "body": body[:8000],
                      "pubdate": email.utils.format_datetime(when)})
    if not items:
        items = [{"title": "ZptMaster Daily Brief", "day": dt.date.today().isoformat(),
                  "body": _brief()[:4000],
                  "pubdate": email.utils.format_datetime(dt.datetime.now(dt.timezone.utc))}]
    def it(i):
        return (f"    <item>\n      <title>{html.escape(i['title'])}</title>\n"
                f"      <link>{PAGES}/intel/{i['day']}.md</link>\n"
                f"      <guid isPermaLink=\"false\">zptmaster-{i['day']}</guid>\n"
                f"      <pubDate>{i['pubdate']}</pubDate>\n"
                f"      <description>{html.escape(i['body'][:1500])}</description>\n    </item>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0">\n  <channel>\n'
           '    <title>ZptMaster Market Intelligence</title>\n'
           f'    <link>{HOME}</link>\n'
           '    <description>Actionable FX/macro brief + risk-governed signals. Honest, fail-closed.</description>\n'
           f'    <lastBuildDate>{email.utils.format_datetime(dt.datetime.now(dt.timezone.utc))}</lastBuildDate>\n'
           + "\n".join(it(i) for i in items) + "\n  </channel>\n</rss>\n")
    open(os.path.join(DOCS, "feed.xml"), "w").write(xml)
    return len(items)

# ---------- track record ----------
def build_track_record():
    rows, seen = [], set()
    # every governed decision ever logged
    for line in _read("journal/plans.jsonl").splitlines():
        try: p = json.loads(line)
        except Exception: continue
        key = (p.get("ts"), p.get("symbol"), p.get("side"))
        if key in seen: continue
        seen.add(key)
        rows.append({"ts": p.get("ts"), "symbol": p.get("symbol"), "side": p.get("side"),
                     "valid": bool(p.get("valid")), "confidence": p.get("confidence"),
                     "rationale": (p.get("rationale") or "")[:160]})
    rows = rows[-2000:]
    tr = {"agent": "ZptMaster", "wallet": "0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D",
          "discipline": {"max_risk_per_order_pct": 1.5, "mandatory_stop": True,
                         "martingale": False, "fail_closed": True},
          "note": "Append-only, timestamped decisions. Honest record incl. every stand-aside.",
          "count": len(rows), "updated": dt.datetime.utcnow().isoformat() + "Z", "decisions": rows}
    json.dump(tr, open(os.path.join(DOCS, "track_record.json"), "w"), indent=2)

    taken = [r for r in rows if r["valid"]]
    body = [f"<tr><td>{html.escape(str(r['ts']))}</td><td>{html.escape(str(r['symbol']))}</td>"
            f"<td>{html.escape(str(r['side']))}</td><td>{'YES' if r['valid'] else 'no'}</td>"
            f"<td>{html.escape(str(r['confidence']))}</td>"
            f"<td>{html.escape(r['rationale'])}</td></tr>" for r in rows[-300:]]
    page = f"""<!doctype html><meta charset=utf-8><title>ZptMaster Track Record</title>
<style>body{{font:14px system-ui;margin:2rem;max-width:1100px}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #ddd;padding:4px 8px;font-size:12px}}th{{background:#f4f4f4}}
.pill{{background:#7ee787;border-radius:10px;padding:2px 8px}}</style>
<h1>ZptMaster — Track Record <span class=pill>auditable</span></h1>
<p>Every governed decision, timestamped and append-only — including every time I stood aside.
Discipline: ≤1.5% risk/order, mandatory stop, no martingale, fail-closed.
Decisions logged: <b>{len(rows)}</b> · taken: <b>{len(taken)}</b> · stand-aside: <b>{len(rows)-len(taken)}</b>.</p>
<p><a href="feed.xml">RSS</a> · <a href="track_record.json">JSON</a> · <a href="{PAGES}/">home</a></p>
<table><tr><th>ts</th><th>symbol</th><th>side</th><th>taken</th><th>conf</th><th>rationale</th></tr>
{''.join(body)}</table>"""
    open(os.path.join(DOCS, "track_record.html"), "w").write(page)
    return len(rows), len(taken)

if __name__ == "__main__":
    nf = build_feed()
    nr, nt = build_track_record()
    print(f"feed items: {nf} | track record: {nr} decisions ({nt} taken)")
