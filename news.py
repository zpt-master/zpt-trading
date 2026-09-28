"""Actionable FX/macro news monitor. Sources: Google News RSS + WSJ Markets RSS.
Scores headlines; sets pause_news.flag when a high-impact event is detected so
the trading engine avoids opening new positions into event risk.
Also feeds headlines to the strategy as a sentiment overlay.
Zero deps. Writes logs/news-YYYY-MM-DD.jsonl"""
import json, os, re, urllib.request
from datetime import datetime, timezone

UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
FEEDS=[
 "https://news.google.com/rss/search?q=forex+OR+%22central+bank%22+OR+%22interest+rate%22+OR+CPI+OR+%22nonfarm+payrolls%22&hl=en-US&gl=US&ceid=US:en",
 "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
 "https://www.investing.com/rss/news_1.rss",
]
HIGH=["fomc","federal reserve","rate decision","rate hike","rate cut","cpi","inflation",
      "nonfarm","non-farm","payroll","gdp","ecb","bank of england","boj","powell","lagarde",
      "unemployment","tariff","sanction","recession","opec"]
PAIRS={"EUR":"eur","USD":"usd","GBP":"gbp","JPY":"jpy","AUD":"aud","NZD":"nzd","CAD":"cad",
       "CHF":"chf","XAU":"gold"}

def fetch(url, timeout=12):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            return r.read().decode("utf-8","ignore")
    except Exception as e:
        return ""

def parse_rss(xml):
    out=[]
    for m in re.finditer(r"<item>(.*?)</item>", xml, re.S):
        b=m.group(1)
        t=re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", b, re.S)
        l=re.search(r"<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", b, re.S)
        d=re.search(r"<pubDate>(.*?)</pubDate>", b, re.S)
        if t:
            out.append({"title":re.sub(r"<.*?>","",t.group(1)).strip(),
                        "url":(l.group(1).strip() if l else ""),
                        "ts":(d.group(1).strip() if d else "")})
    return out

def score(title):
    t=title.lower()
    hits=[k for k in HIGH if k in t]
    pairs=[p for p,k in PAIRS.items() if k in t]
    return len(hits)*2+len(pairs), hits, pairs

def run():
    os.makedirs("logs", exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path=f"logs/news-{stamp}.jsonl"
    items=[]
    for u in FEEDS:
        xml=fetch(u)
        if xml: items+=parse_rss(xml)
    # dedupe by title
    seen=set(); uniq=[]
    for it in items:
        k=it["title"][:60].lower()
        if k and k not in seen: seen.add(k); uniq.append(it)
    high=[]
    with open(path,"a") as f:
        for it in uniq:
            s,hits,pairs=score(it["title"])
            rec={**it,"score":s,"high_impact":hits,"pairs":pairs}
            f.write(json.dumps(rec)+"\n")
            if s>=4: high.append(rec)
    print(f"{datetime.now(timezone.utc).isoformat()} news: {len(uniq)} items ({len(items)} raw), {len(high)} high-impact")
    for h in high[:8]: print(f"  [{h['score']}] {h['title'][:105]}")
    flag="pause_news.flag"
    if high:
        open(flag,"w").write(json.dumps({"ts":datetime.now(timezone.utc).isoformat(),
            "reason":high[0]["title"],"count":len(high)}))
        print(f"  -> PAUSE FLAG set")
    elif os.path.exists(flag):
        os.remove(flag); print("  -> pause flag cleared")
    return high

if __name__=="__main__":
    run()
