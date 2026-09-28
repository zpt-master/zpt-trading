"""Append-only journal of risk-governed trade plans (paper until MT5 exists)."""
import os, json, time, csv
JOURNAL_DIR="journal"
def _ensure(): os.makedirs(JOURNAL_DIR, exist_ok=True)
def log_plan(plan, source="intel"):
    _ensure()
    row={"ts":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
         "symbol":plan.symbol,"side":plan.side,"entry":plan.entry,"stop":plan.stop,
         "target":plan.target,"rr":plan.rr,"size_lots":plan.size_lots,
         "risk_usd":plan.risk_usd,"confidence":plan.confidence,"valid":plan.valid,
         "source":source,"rationale":plan.rationale}
    with open(os.path.join(JOURNAL_DIR,"plans.jsonl"),"a") as f:
        f.write(json.dumps(row)+"\n")
    return row
def daily_summary():
    _ensure(); p=os.path.join(JOURNAL_DIR,"plans.jsonl")
    if not os.path.exists(p): return {"plans":0,"valid":0}
    rows=[json.loads(l) for l in open(p) if l.strip()]
    today=time.strftime("%Y-%m-%d",time.gmtime())
    t=[r for r in rows if r["ts"].startswith(today)]
    return {"plans":len(t),"valid":sum(1 for r in t if r["valid"]),
            "symbols":sorted({r["symbol"] for r in t})}
