"""Reconcile x402 payment proofs into a settlement ledger.
Reads logs/intel_payments.jsonl, counts calls, computes expected USDC at the
configured price, and writes logs/settlement.json + a human summary. This is
what you hand to a buyer/creator to prove revenue.
"""
import json, os
from datetime import datetime, timezone
HERE=os.path.dirname(os.path.abspath(__file__))
def run():
    cfg=json.load(open(os.path.join(HERE,"config.json")))
    price=float(cfg["x402"]["intel_price_usdc"])
    p=os.path.join(HERE,"logs","intel_payments.jsonl")
    rows=[]
    if os.path.exists(p):
        for line in open(p):
            try: rows.append(json.loads(line))
            except Exception: pass
    by_day={}
    for r in rows:
        day=(r.get("ts","")[:10])
        by_day[day]=by_day.get(day,0)+1
    out={"ts":datetime.now(timezone.utc).isoformat(),"wallet":cfg["wallet"],
         "price_usdc":price,"paid_calls":len(rows),
         "expected_usdc":round(len(rows)*price,4),
         "by_day":by_day}
    os.makedirs(os.path.join(HERE,"logs"),exist_ok=True)
    json.dump(out,open(os.path.join(HERE,"logs","settlement.json"),"w"),indent=2)
    print(f"settlement: {len(rows)} paid calls -> {out['expected_usdc']} USDC owed to {cfg['wallet']}")
    return out
if __name__=="__main__": run()
