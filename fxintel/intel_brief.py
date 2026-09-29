#!/usr/bin/env python3
"""fxintel/intel_brief.py - the PRODUCT: one fused actionable brief.

Fuses genesis priority #1 (news) + #2 (risk-governed market view) into a single
artifact served BOTH free (funnel: docs/brief.json) and paid (x402 /intel reads
the richer intel/latest.md). Also emits a machine-readable JSON so any buyer
(agent or human) can consume it programmatically.

Outputs:
  intel/latest.md          - human brief (free funnel + paid payload)
  docs/brief.json          - machine JSON (free feed + x402 manifest companion)
CLI: python3 -m fxintel.intel_brief
"""
from __future__ import annotations
import os, sys, json, glob, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPORTS = os.path.join(ROOT, "reports")
INTEL = os.path.join(ROOT, "intel"); os.makedirs(INTEL, exist_ok=True)
DOCS = os.path.join(ROOT, "docs"); os.makedirs(DOCS, exist_ok=True)


def read_news_brief():
    p = os.path.join(REPORTS, "news_brief.md")
    return open(p).read() if os.path.exists(p) else "_no news brief yet_"


def latest_signals():
    """Read the newest fxintel signal/journal artifact if present."""
    for pat in ("fxintel/data/signals_*.json", "journal/plans.jsonl", "reports/signals.json"):
        fs = sorted(glob.glob(os.path.join(ROOT, pat)))
        if fs:
            try:
                txt = open(fs[-1]).read().strip()
                if txt.startswith("["):
                    return json.loads(txt)
                return [json.loads(l) for l in txt.splitlines() if l.strip()]
            except Exception:
                pass
    return []


def build():
    now = dt.datetime.now(dt.timezone.utc)
    news = read_news_brief()
    sig = latest_signals()
    # pull the actionable block out of the news markdown
    act = []
    for line in news.splitlines():
        if line.startswith("- **[") :
            try:
                sc = int(line.split("**[", 1)[1].split("]", 1)[0])
                title = line.split("](", 1)[0].split("]", 1)[1].strip()
                url = line.split("](", 1)[1].split(")", 1)[0]
                act.append({"score": sc, "title": title, "url": url})
            except Exception:
                pass
    L = [f"# Conway Intelligence — Actionable Brief",
         f"_{now.strftime('%Y-%m-%d %H:%M UTC')} · sources: 8 free feeds + gold/forex market view_", "",
         f"## Top {min(10,len(act))} actionable drivers"]
    for a in act[:10]:
        L.append(f"- **[{a['score']}]** {a['title']}  \n  {a['url']}")
    L += ["", "## Risk-governed market view",
          ("_No aligned signal — correctly standing aside (capital preserved)._" if not sig
           else "```json\n" + json.dumps(sig[:5], indent=2) + "\n```"), "",
          "## Full brief", "", news]
    md = "\n".join(L)
    open(os.path.join(INTEL, "latest.md"), "w").write(md)

    payload = {
        "generated": now.isoformat(),
        "actionable": act[:10],
        "market_view": sig[:5],
        "disclaimer": "Informational only. Not financial advice. No proven trading edge claimed.",
        "paid_endpoints": {"intel": "0.02 USDC", "signal": "0.005 USDC"},
        "payTo": "0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D",
        "network": "eip155:8453", "asset": "USDC 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    }
    json.dump(payload, open(os.path.join(DOCS, "brief.json"), "w"), indent=2)
    return len(act), len(sig)


if __name__ == "__main__":
    a, s = build()
    print(f"intel_brief: {a} actionable headlines, {s} signals -> intel/latest.md + docs/brief.json")
