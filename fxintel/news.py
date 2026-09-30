#!/usr/bin/env python3
"""fxintel/news.py - actionable market-news monitor (free RSS, no API key).

Genesis priority #1: "Theo dõi tin tức - tổng hợp tin tức thị trường, cong nghe,
tai chinh co gia tri hanh dong (actionable)."

Design:
  * Fan-in from multiple free RSS feeds (reuters/marketwatch/forexlive/coindesk/...).
  * Extract title+link+time; de-duplicate by normalized title.
  * Score ACTIONABILITY: high-impact macro/event keywords (rate, CPI, NFP, war,
    crash, ban, hack, ETF, halving, default, sanction...) weighted; emit
    [ACTIONABLE] vs [info] tags with the matched driver + affected assets.
  * Persist to SQLite so we never repeat a headline; write a markdown brief.
CLI:
  python3 -m fxintel.news                 # collect + write reports/news_brief.md
  python3 -m fxintel.news --hours 6       # only last N hours
"""
from __future__ import annotations
import os, sys, re, json, sqlite3, hashlib, urllib.request, datetime as dt
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPORTS = os.path.join(ROOT, "reports"); os.makedirs(REPORTS, exist_ok=True)
DB = os.path.join(REPORTS, "news.sqlite")
UA = {"User-Agent": "Mozilla/5.0 (compatible; ZptIntel/1.0)"}

FEEDS = {
    "reuters-gn": "https://news.google.com/rss/search?q=when:1d+reuters+business&hl=en-US&gl=US&ceid=US:en",
    "marketwatch": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "cnbc-markets": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "fxstreet": "https://www.fxstreet.com/rss/news",
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "investing-news": "https://www.investing.com/rss/news.rss",
    "yahoo-fin": "https://finance.yahoo.com/news/rssindex",
}

# driver -> (weight, affected assets)
DRIVERS = [
    ("rate hike|rate cut|fed funds|fomc|interest rate|powell", 3, "USD,GC,EQ"),
    ("inflation|cpi|ppi|pce", 3, "USD,GC,EQ"),
    ("nonfarm|payroll|nfp|unemployment|jobs report", 3, "USD,EQ"),
    ("gdp|recession|stagflation", 3, "EQ,USD"),
    ("trump|tariff|sanction|embargo", 3, "EQ,GC,OIL"),
    ("war|strike|attack|invasion|missile|geopolit", 3, "GC,OIL,EQ"),
    ("crash|plunge|selloff|sell-off|bear market|recession", 3, "EQ"),
    ("default|debt ceiling|downgrade|bankrupt|bailout", 3, "EQ,USD"),
    ("etf approve|spot etf|sec approve|regulat|ban crypto|crackdown", 3, "BTC,ETH"),
    ("halving|hard fork|upgrade|mainnet|airdrop", 2, "BTC,ETH"),
    ("hack|exploit|stolen|breach|rug", 3, "BTC,ETH"),
    ("all-time high|record high|rally|surge|breakout", 2, "EQ,BTC,GC"),
    ("opec|oil supply|crude|brent", 2, "OIL"),
    ("ecb|boj|boe|pboc|central bank", 2, "USD,EUR,JPY"),
    ("gold|bullion|xau", 2, "GC"),
    ("bitcoin|btc|ethereum|eth|crypto", 1, "BTC,ETH"),
]
NUM_RE = re.compile(r"\b\d+(\.\d+)?\s?%|\$\d|\b\d+\s?(bps|basis points|trillion|billion)\b", re.I)


def _db():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS seen(h TEXT PRIMARY KEY, ts TEXT, title TEXT, link TEXT, src TEXT, score INT, drivers TEXT)")
    return c


def _norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t.lower())).strip()


def fetch(feed_url, timeout=15):
    raw = urllib.request.urlopen(urllib.request.Request(feed_url, headers=UA), timeout=timeout).read()
    root = ET.fromstring(raw)
    items = []
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag in ("item", "entry"):
            title = link = pub = ""
            for ch in it:
                ct = ch.tag.split("}")[-1]
                if ct == "title" and ch.text: title = ch.text.strip()
                elif ct == "link":
                    link = (ch.text or ch.attrib.get("href", "")).strip()
                elif ct in ("pubDate", "published", "updated", "date") and ch.text:
                    pub = ch.text.strip()
            if title:
                items.append({"title": title, "link": link, "pub": pub})
    return items


def score(title):
    low = title.lower()
    matched = []
    total = 0
    for pat, w, assets in DRIVERS:
        if re.search(pat, low):
            matched.append((pat.split("|")[0], assets)); total += w
    if NUM_RE.search(title): total += 1; matched.append(("quant", "-"))
    return min(total, 9), matched


def collect(hours=24):
    c = _db()
    now = dt.datetime.now(dt.timezone.utc)
    new = []
    for src, url in FEEDS.items():
        try:
            items = fetch(url)
        except Exception as e:
            print(f"  {src}: ERR {str(e)[:50]}"); continue
        got = 0
        for it in items:
            t = it["title"]
            h = hashlib.sha256(_norm(t).encode()).hexdigest()[:16]
            if c.execute("SELECT 1 FROM seen WHERE h=?", (h,)).fetchone():
                continue
            sc, dr = score(t)
            ts = ""
            if it["pub"]:
                try: ts = parsedate_to_datetime(it["pub"]).astimezone(dt.timezone.utc).isoformat()
                except Exception: ts = it["pub"]
            c.execute("INSERT OR IGNORE INTO seen VALUES(?,?,?,?,?,?,?)",
                      (h, ts or now.isoformat(), t, it["link"], src, sc, json.dumps(dr)))
            new.append({"title": t, "link": it["link"], "src": src, "score": sc, "drivers": dr, "ts": ts})
            got += 1
        c.commit()
        print(f"  {src}: {got} new / {len(items)} items")
    return new


def brief(new, hours=24):
    new.sort(key=lambda x: -x["score"])
    act = [n for n in new if n["score"] >= 3]
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    L = [f"# Market Brief — {now}", "",
         f"**{len(new)} new headlines**, **{len(act)} actionable** (score >= 3).", ""]
    L.append("## ACTIONABLE")
    for n in act[:25]:
        dr = ", ".join(f"{d}->{a}" for d, a in n["drivers"][:3])
        L.append(f"- **[{n['score']}]** [{n['title']}]({n['link']})  \n  _({n['src']}; {dr})_")
    L.append(""); L.append("## Other notable")
    for n in [x for x in new if x["score"] < 3][:15]:
        L.append(f"- [{n['title']}]({n['link']}) _({n['src']})_")
    open(os.path.join(REPORTS, "news_brief.md"), "w").write("\n".join(L) + "\n")
    return len(act)


def main(argv):
    hours = 24
    if "--hours" in argv: hours = int(argv[argv.index("--hours") + 1])
    print("collecting feeds...")
    new = collect(hours)
    a = brief(new, hours)
    print(f"wrote reports/news_brief.md  ({len(new)} new, {a} actionable)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
