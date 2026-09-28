"""Adaptive strategy selector + live circuit-breaker.

Instead of a fixed strategy, this evaluates a panel of strategy families on the
most RECENT window of cached data for each symbol and picks the one with the
best recent expectancy — but only if it clears a floor. It also tracks LIVE
results per (symbol,family) and disables combos whose realized avgR goes
negative over a minimum sample. This makes the engine self-correcting rather
than dependent on a single historically-chosen rule.

Outputs selector_state.json: {symbol: {family, rr, sm, reason, live_n, live_avgR}}
"""
import json, os, glob, itertools
from datetime import datetime, timezone
import backtest_common as bc   # shared simulate/stats/families

HERE=os.path.dirname(os.path.abspath(__file__))
STATE=os.path.join(HERE,"selector_state.json")
JOURNAL=os.path.join(HERE,"logs","trades.jsonl")

RECENT_BARS=1500        # evaluate only the recent window
MIN_TRADES=15           # need this many OOS trades to trust a family
FLOOR_AVGR=0.08         # must beat this expectancy
LIVE_MIN_N=10           # live sample before we judge
LIVE_DISABLE_AVGR=-0.05 # disable if live expectancy sinks below this

def recent_eval(sym, itv="1h"):
    p=os.path.join(HERE,"cache",f"{sym}_{itv}.json")
    if not os.path.exists(p): return None
    cs=json.load(open(p))[-RECENT_BARS:]
    if len(cs)<400: return None
    best=None
    for name,ent in bc.FAMILIES.items():
        for rr,sm in itertools.product([1.0,1.5,2.0],[1.5,2.0]):
            R=bc.simulate(cs,ent,rr,sm,260)
            st=bc.stats(R)
            if not st or st["n"]<MIN_TRADES: continue
            if st["avgR"]<FLOOR_AVGR: continue
            score=st["avgR"] - 0.01*abs(st["dd"])   # risk-adjusted preference
            if best is None or score>best["score"]:
                best={"family":name,"rr":rr,"sm":sm,"avgR":st["avgR"],
                      "wr":st["wr"],"n":st["n"],"dd":st["dd"],"score":round(score,3)}
    return best

def live_stats():
    """Aggregate realized R per (symbol,family) from the journal."""
    out={}
    if not os.path.exists(JOURNAL): return out
    for line in open(JOURNAL):
        try: t=json.loads(line)
        except Exception: continue
        if t.get("event")!="close": continue
        key=(t.get("symbol","").replace("+",""), t.get("family","?"))
        pnl=t.get("pnl",0.0)
        out.setdefault(key,[]).append(pnl)
    return out

def build():
    syms=[os.path.basename(f).split("_")[0] for f in glob.glob(os.path.join(HERE,"cache","*_1h.json"))]
    syms=sorted(set(syms))
    live=live_stats()
    state={"ts":datetime.now(timezone.utc).isoformat(),"symbols":{}}
    for s in syms:
        ev=recent_eval(s)
        if not ev:
            state["symbols"][s]={"enabled":False,"reason":"no positive-expectancy family in recent window"}
            continue
        # live circuit-breaker for this combo
        lk=(s,ev["family"]); lr=live.get(lk,[])
        avgR=(sum(lr)/len(lr)) if lr else None
        dis = (avgR is not None and len(lr)>=LIVE_MIN_N and avgR<LIVE_DISABLE_AVGR)
        state["symbols"][s]={"enabled": not dis,"family":ev["family"],"rr":ev["rr"],"sm":ev["sm"],
            "recent_avgR":ev["avgR"],"recent_wr":ev["wr"],"recent_n":ev["n"],
            "live_n":len(lr),"live_avgR":(round(avgR,3) if avgR is not None else None),
            "reason": "live circuit-breaker tripped" if dis else "recent positive expectancy"}
    json.dump(state,open(STATE,"w"),indent=2)
    return state

if __name__=="__main__":
    st=build()
    on=[s for s,v in st["symbols"].items() if v["enabled"]]
    print(f"selector: {len(on)}/{len(st['symbols'])} symbols enabled: {on}")
    for s,v in st["symbols"].items():
        print(f"  {s:8} {'ON ' if v['enabled'] else 'off'} {v.get('family','-'):14} {v.get('reason','')}")
