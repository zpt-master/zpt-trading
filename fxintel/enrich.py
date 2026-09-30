#!/usr/bin/env python3
"""fxintel/enrich.py - enrich headlines with asset tags + polarity.

Buyers want to know WHICH asset and WHICH direction. This tags each headline
with instruments (USD, EUR, GOLD, OIL, BTC...) and a crude polarity from a
curated finance lexicon, then ranks by (actionability * |polarity|).
Deterministic, dependency-free, auditable.
"""
import re, json, os, sys

INSTR = {
    "USD": r"\b(dollar|usd|fed|fomc|powell|treasury|nonfarm|nfp|cpi|inflation|yields?)\b",
    "EUR": r"\b(euro|eur|ecb|lagarde|eurozone|germany|german)\b",
    "GBP": r"\b(pound|gbp|boe|bailey|uk|britain|british)\b",
    "JPY": r"\b(yen|jpy|boj|japan|ueda)\b",
    "GOLD": r"\b(gold|xau|bullion|precious metals?)\b",
    "OIL": r"\b(oil|crude|wti|brent|opec|barrel)\b",
    "BTC": r"\b(bitcoin|btc|crypto|ethereum|eth)\b",
    "EQUITY": r"\b(stocks?|equit(y|ies)|s&p|nasdaq|dow|earnings)\b",
}
POS = r"\b(rally|surge|soar|jump|gain|beat|strong|upgrade|record high|bullish|rebound|boost|optimis)\b"
NEG = r"\b(plunge|crash|fall|drop|slump|miss|weak|downgrade|bearish|recession|sell-?off|fear|warn|loss)\b"


def tag(title: str):
    t = (title or "").lower()
    assets = [k for k, pat in INSTR.items() if re.search(pat, t)]
    p = len(re.findall(POS, t)); n = len(re.findall(NEG, t))
    polarity = 0
    if p or n:
        polarity = (p - n) / max(p + n, 1)
    return assets, round(polarity, 2)


def enrich(items):
    out = []
    for it in items:
        assets, pol = tag(it.get("title", ""))
        it = dict(it); it["assets"] = assets; it["polarity"] = pol
        it["rank"] = round(float(it.get("score", 0)) * (1 + abs(pol)), 2)
        out.append(it)
    out.sort(key=lambda x: x.get("rank", 0), reverse=True)
    return out


def to_markdown(items, top=25):
    lines = []
    for it in items[:top]:
        a = ",".join(it.get("assets", [])) or "-"
        p = it.get("polarity", 0)
        arrow = "▲" if p > 0.15 else ("▼" if p < -0.15 else "•")
        lines.append(f"- **[{it.get('score','?')}] {a} {arrow}** [{it.get('title','')}]({it.get('url','#')})")
    return "\n".join(lines)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "reports/news_brief.json"
    if os.path.exists(src):
        items = json.load(open(src))
        if isinstance(items, dict):
            items = items.get("items", [])
        en = enrich(items)
        open("reports/news_enriched.md", "w").write("# Enriched actionable news\n\n" + to_markdown(en) + "\n")
        print(f"enriched {len(en)} items -> reports/news_enriched.md")
    else:
        print("no source; demo:", to_markdown(enrich([
            {"title": "Gold surges as Fed signals rate cuts", "score": 5, "url": "#"},
            {"title": "Oil plunges on OPEC supply fears", "score": 4, "url": "#"},
        ])))
