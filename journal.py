"""Closed-trade reconciliation + journal.

Problem it solves: the bridge reports OPEN positions, but the daily ledger
(profit vs high-water) and the consecutive-loss cooldown need REALIZED,
CLOSED-trade P&L. This module diffs successive position snapshots, detects
closes, attributes realized P&L to the trade, and updates risk.py state.

Run every cycle (engine calls reconcile()) and in the 15-min loop.
Writes trades.jsonl (append-only journal).
"""
import json, os, time, urllib.request
from datetime import datetime, timezone

HERE=os.path.dirname(os.path.abspath(__file__))
BRIDGE="http://localhost:4790"; TOKEN=os.environ.get("MT5_TOKEN","change-me-shared-secret")
POSFILE=os.path.join(HERE,"open_positions.json")
JOURNAL=os.path.join(HERE,"logs","trades.jsonl")

def bridge(path):
    r=urllib.request.Request(BRIDGE+path,headers={"Authorization":f"Bearer {TOKEN}"})
    return json.load(urllib.request.urlopen(r,timeout=15))

def _key(p):
    return f"{p.get('symbol')}|{p.get('type') or p.get('side')}|{p.get('volume')}"

def reconcile():
    st=bridge("/mt5/state"); snap=st["snapshot"]
    positions={ _key(p): p for p in (snap.get("positions") or []) }
    prev=json.load(open(POSFILE)) if os.path.exists(POSFILE) else {}

    closed=[]
    for k,p in list(prev.get("positions",{}).items()):
        if k not in positions:                      # it disappeared -> closed
            closed.append(p)
    # snapshots of open positions carry an unrealized 'profit'; when a position
    # vanishes the bridge has already settled it, so we approximate realized
    # P&L by the last known profit of that position (best available signal).
    os.makedirs(os.path.dirname(JOURNAL),exist_ok=True)
    realized_today=0.0
    for c in closed:
        pnl=float(c.get("profit",0.0) or 0.0)
        realized_today+=pnl
        rec={"ts":datetime.now(timezone.utc).isoformat(),"event":"close",
             "symbol":c.get("symbol"),"side":c.get("type") or c.get("side"),
             "volume":c.get("volume"),"pnl":pnl,"ticket":c.get("ticket")}
        open(JOURNAL,"a").write(json.dumps(rec)+"\n")

    json.dump({"ts":datetime.now(timezone.utc).isoformat(),"positions":positions},
              open(POSFILE,"w"), indent=2)

    # update risk state with realized results
    if closed:
        import risk
        s=risk.load()
        for c in closed:
            pnl=float(c.get("profit",0.0) or 0.0)
            s["day_realized"]=s.get("day_realized",0.0)+pnl
            if pnl<0:
                s["consecutive_losses"]=s.get("consecutive_losses",0)+1
                if s["consecutive_losses"]>=risk.MAX_CONSEC_LOSSES:
                    s["halted"]=True; s["halt_reason"]="3 consecutive losses - 24h cooldown"
            elif pnl>0:
                s["consecutive_losses"]=0
        risk.save(s)
    return {"closed":len(closed),"realized":round(realized_today,2),"open":len(positions)}

if __name__=="__main__":
    r=reconcile(); print(datetime.now(timezone.utc).isoformat(),"reconcile",r)
