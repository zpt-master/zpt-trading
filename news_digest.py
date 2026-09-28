#!/usr/bin/env python3
"""Actionable market/tech/finance news digest.
Pulls free RSS feeds, filters to actionable items, writes reports/news_digest.md.
Degrades gracefully (never crashes) if a feed is unreachable."""
import os, sys, time, json, re, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEEDS = [
    ("Market",  "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
    ("Tech",    "https://hnrss.org/frontpage"),
    ("Finance", "https://www.investing.com/rss/news_25.rss"),
    ("FX",      "https://www.dailyfx.com/feeds/market-news"),
]
# keywords that make an item ACTIONABLE rather than noise
ACTION = ["fed","rate","inflation","cpi","jobs","nfp","ecb","boj","dollar","usd","eur",
          "gold","oil","tariff","sanction","earnings","gdp","recession","layoff","ai",
          "chip","nvidia","crypto","bitcoin","yield","treasury","opec","war","ban"]

def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (compatible; ConwayIntel/1.0)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def parse(xml_bytes):
    out=[]
    try:
        root=ET.fromstring(xml_bytes)
    except Exception:
        return out
    items = root.iter("item")
    for it in items:
        t = it.findtext("title") or ""
        l = it.findtext("link") or ""
        d = it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date") or ""
        if t:
            out.append({"title":re.sub(r"\s+"," ",t).strip(),"link":l.strip(),"date":d.strip()})
    return out

def score(title):
    tl=title.lower()
    return sum(1 for k in ACTION if k in tl)

def main():
    now=datetime.now(timezone.utc)
    sections={}
    hits=0
    for name,url in FEEDS:
        try:
            items=parse(fetch(url))
            hits+=len(items)
        except Exception as e:
            sections[name]=("UNREACHABLE", [])
            continue
        scored=sorted(items, key=lambda x:-score(x["title"]))
        sections[name]=("ok", scored[:8])
    lines=["# Actionable News Digest", f"_Generated {now.strftime('%Y-%m-%d %H:%M UTC')}_","",
           f"Sources reachable: {sum(1 for v in sections.values() if v[0]=='ok')}/{len(FEEDS)} · items seen: {hits}",""]
    for name,(status,items) in sections.items():
        lines.append(f"## {name} ({status})")
        if not items:
            lines.append("- _no items / feed unreachable_")
        for it in items:
            s=score(it["title"])
            tag="**[ACTIONABLE]** " if s>=2 else ""
            lines.append(f"- {tag}{it['title']}")
        lines.append("")
    lines.append("## Note")
    lines.append("**[ACTIONABLE]** = 2+ market/finance keywords. Curated for decision value, not completeness.")
    os.makedirs("reports", exist_ok=True)
    with open("reports/news_digest.md","w") as f:
        f.write("\n".join(lines))
    print(f"wrote reports/news_digest.md ({len(lines)} lines, {hits} items seen)")

if __name__=="__main__":
    main()
