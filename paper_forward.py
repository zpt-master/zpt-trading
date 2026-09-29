#!/usr/bin/env python3
"""paper_forward.py - paper-forward validation of the one sign-stable candidate.

Candidate (from reports/edge_candidates.json, walk-forward 70/30 on real bars):
  EMA(20/50) trend + mandatory 1.5xATR stop + RR=3.0 target, no RSI filter.

Purpose: the 70/30 test is in-sample-ish (params picked on the same history).
The only honest next step is FORWARD testing: run the exact rule on bars that
arrive AFTER selection, journal every trade, and report cumulative expectancy.
Fail-closed: if expectancy degrades, it reports NO EDGE and keeps capital safe.

Outputs: journal/paper_forward.jsonl (append-only), reports/paper_forward.md
"""
from __future__ import annotations
import os, sys, json, datetime as dt

ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT); sys.path.insert(0, ROOT)
SYMBOLS = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","XAUUSD"]
RISK_PCT = 1.0
COST_PIPS = 1.2
PIP = {"XAUUSD":0.10,"EURJPY":0.01,"GBPJPY":0.01}
PARAMS = {"tf":20,"ts":50,"rr":3.0,"use_rsi":False,"rsi_lo":0,"rsi_hi":100}
STATE = "journal/paper_forward_state.json"
LOG = "journal/paper_forward.jsonl"

def pip_of(s): return PIP.get(s,0.0001)
def ema(xs,n):
    if len(xs)<n: return None
    k=2.0/(n+1); e=sum(xs[:n])/n
    for x in xs[n:]: e=x*k+e*(1-k)
    return e
def atr(bars,n=14):
    if len(bars)<n+1: return None
    trs=[max(bars[i]["h"]-bars[i]["l"],abs(bars[i]["h"]-bars[i-1]["c"]),abs(bars[i]["l"]-bars[i-1]["c"])) for i in range(1,len(bars))]
    return sum(trs[-n:])/n if len(trs)>=n else None
def atr_of(b): return None

def load(sym,n=1000):
    try:
        from fxintel.bars import load as _l
        raw,src=_l(sym,"H1",n,allow_synthetic=False)
    except Exception: return [], "none"
    if not raw: return [], src
    out=[]
    for b in raw:
        o=b.get("o",b.get("open"));h=b.get("h",b.get("high"));l=b.get("l",b.get("low"));c=b.get("c",b.get("close"))
        if None not in (o,h,l,c): out.append({"o":o,"h":h,"l":l,"c":c,"t":b.get("t",b.get("time"))})
    return out, src

def main():
    os.makedirs("journal",exist_ok=True)
    st=json.load(open(STATE)) if os.path.exists(STATE) else {"last_index":{}, "trades":[], "open":{}}
    summary={}
    for s in SYMBOLS:
        bars,src=load(s)
        if len(bars)<220: summary[s]={"status":"no data","src":src}; continue
        last=st["last_index"].get(s,200)
        start=max(last,210); new=bars[start:]
        made=0
        # simple event loop over newly arrived bars using FULL history for indicators
        pos=None
        for i in range(start,len(bars)-1):
            b=bars[i]
            if pos is not None:
                hi,lo=b["h"],b["l"]
                hsl=(pos["side"]=="buy" and lo<=pos["stop"]) or (pos["side"]=="sell" and hi>=pos["stop"])
                htp=(pos["side"]=="buy" and hi>=pos["target"]) or (pos["side"]=="sell" and lo<=pos["target"])
                ex=pos["stop"] if hsl else (pos["target"] if htp else None)
                if ex is not None:
                    sg=1 if pos["side"]=="buy" else -1
                    net=(ex-pos["entry"])*sg-COST_PIPS*pip_of(s)
                    R=net/(abs(pos["entry"]-pos["stop"]) or 1e-9)
                    rec={"ts":dt.datetime.now(dt.timezone.utc).isoformat(),"symbol":s,"side":pos["side"],
                         "entry":pos["entry"],"exit":ex,"R":round(R,3),"pnl_pct":round(R*RISK_PCT,3),"src":src}
                    st["trades"].append(rec)
                    with open(LOG,"a") as f: f.write(json.dumps(rec)+"\n")
                    pos=None; made+=1
                    continue
            if pos is None:
                cl=[x["c"] for x in bars[:i+1]]
                ef=ema(cl,20); es=ema(cl,50); a=atr(bars[:i+1],14)
                if ef and es and a and ef!=es:
                    side="buy" if ef>es else "sell"; e=b["c"]; sd=1.5*a; td=3.0*sd
                    stt=e-sd if side=="buy" else e+sd; tgt=e+td if side=="buy" else e-td
                    pos={"side":side,"entry":e,"stop":stt,"target":tgt}
        st["last_index"][s]=len(bars)-1
        summary[s]={"bars":len(bars),"src":src,"new_trades":made}

    # aggregate forward stats across ALL logged trades
    rs=[t["R"] for t in st["trades"]]
    if rs:
        w=[r for r in rs if r>0]; l=[r for r in rs if r<=0]
        eq=peak=mdd=0.0
        for r in rs:
            eq+=r*RISK_PCT; peak=max(peak,eq); mdd=max(mdd,peak-eq)
        agg={"trades":len(rs),"win_rate":round(len(w)/len(rs),3),
             "expectancy_pct":round(sum(rs)/len(rs)*RISK_PCT,4),
             "profit_factor":round(sum(w)/(abs(sum(l)) or 1e-9),3),
             "max_dd_pct":round(mdd,2),"total_return_pct":round(sum(rs)*RISK_PCT,2)}
    else:
        agg={"trades":0}
    json.dump(st,open(STATE,"w"),indent=2)
    if os.path.exists("journal"):
        with open("reports/paper_forward.md","w") as f:
            f.write(f"# Paper-forward validation ({dt.datetime.now(dt.timezone.utc).isoformat()})\n\n")
            f.write(f"Candidate: EMA(20/50), 1.5xATR stop, RR=3.0, cost {COST_PIPS} pips, risk {RISK_PCT}%/trade\n\n")
            f.write(f"## Forward aggregate\n```json\n{json.dumps(agg,indent=2)}\n```\n\n")
            f.write("## Per-symbol this run\n")
            for k,v in summary.items(): f.write(f"- {k}: {v}\n")
            verdict = "POSITIVE forward expectancy - keep paper-testing, do NOT go live without more samples" if agg.get("trades",0)>=30 and agg.get("expectancy_pct",0)>0 else "INSUFFICIENT / NO EDGE - stand aside, capital preserved"
            f.write(f"\n**VERDICT: {verdict}**\n")
            print("paper_forward:",json.dumps(agg)); print("VERDICT:",verdict)
    return agg

if __name__=="__main__": main()
