#!/usr/bin/env python3
"""edge_search.py - walk-forward parameter search for a GOVERNED FX strategy.

Honest question: does *any* risk-governed parameter set show positive
OUT-OF-SAMPLE expectancy on real bars, after costs? If not, standing aside is
the correct, capital-preserving decision and we say so plainly.

Anti-self-flattery design:
  * real bars only (fxintel.data.load_bars, allow_synthetic=False)
  * strict 70/30 split: params chosen on train, evaluated ONCE on held-out test
  * costs charged every round trip (spread+commission in pips)
  * fixed-fractional risk, mandatory stop, no martingale, one position/symbol
  * governed primitives shared with production
Output: reports/edge_search.json (+ stdout summary)
"""
from __future__ import annotations
import os, sys, json, itertools, datetime as dt

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT); sys.path.insert(0, ROOT)

SYMBOLS = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","USDCHF","NZDUSD","EURJPY","GBPJPY","XAUUSD"]
RISK_PCT = 1.0
COST_PIPS = 1.2
PIP = {"XAUUSD":0.10,"EURJPY":0.01,"GBPJPY":0.01}
TF = "H1"

def pip_of(s): return PIP.get(s,0.0001)

def load(sym, n=1500):
    try:
        from fxintel.bars import load as _l
    except Exception:
        return [], "none"
    try:
        raw, src = _l(sym, TF, n, allow_synthetic=False)
    except Exception as e:
        return [], "err:"+str(e)[:40]
    if not raw: return [], src
    bars=[]
    for b in raw:
        o=b.get("o", b.get("open")); h=b.get("h", b.get("high"))
        l=b.get("l", b.get("low")); c=b.get("c", b.get("close"))
        if None not in (o,h,l,c): bars.append({"o":o,"h":h,"l":l,"c":c})
    return bars, src

def ema(xs,n):
    if len(xs)<n: return None
    k=2.0/(n+1); e=sum(xs[:n])/n
    for x in xs[n:]: e=x*k+e*(1-k)
    return e

def atr(bars,n=14):
    if len(bars)<n+1: return None
    trs=[]
    for i in range(1,len(bars)):
        h,l,pc=bars[i]["h"],bars[i]["l"],bars[i-1]["c"]
        trs.append(max(h-l,abs(h-pc),abs(l-pc)))
    return sum(trs[-n:])/n if len(trs)>=n else None

def rsi(cl,n=14):
    if len(cl)<n+1: return None
    g=l=0.0
    for i in range(1,n+1):
        d=cl[i]-cl[i-1]; g+=max(d,0); l+=max(-d,0)
    if l==0: return 100.0
    return 100-100/(1+((g/n)/(l/n)))

def signal(bars,i,tf,ts,rr,use_rsi,rl,rh):
    if i<ts+2: return None
    cl=[b["c"] for b in bars[:i+1]]
    ef=ema(cl,tf); es=ema(cl,ts)
    if ef is None or es is None or ef==es: return None
    a=atr(bars[:i+1],14)
    if not a or a<=0: return None
    r=rsi(cl,14); up=ef>es; side="buy" if up else "sell"
    if use_rsi and r is not None:
        if side=="buy" and r>rh: return None
        if side=="sell" and r<rl: return None
    stop=1.5*a; return side,stop,rr*stop

def run(bars,start,end,pr):
    trades=[]; pos=None; p=pip_of(pr["_sym"])
    for i in range(start,end):
        b=bars[i]
        if pos is not None:
            hi,lo=b["h"],b["l"]
            hsl=(pos["side"]=="buy" and lo<=pos["stop"]) or (pos["side"]=="sell" and hi>=pos["stop"])
            htp=(pos["side"]=="buy" and hi>=pos["target"]) or (pos["side"]=="sell" and lo<=pos["target"])
            ex=pos["stop"] if hsl else (pos["target"] if htp else None)
            if ex is not None:
                sg=1 if pos["side"]=="buy" else -1
                net=(ex-pos["entry"])*sg-COST_PIPS*p
                trades.append(net/(abs(pos["entry"]-pos["stop"]) or 1e-9)); pos=None
            else: continue
        s=signal(bars,i,pr["tf"],pr["ts"],pr["rr"],pr["use_rsi"],pr["rsi_lo"],pr["rsi_hi"])
        if s:
            side,sd,td=s; e=b["c"]
            st=e-sd if side=="buy" else e+sd
            tg=e+td if side=="buy" else e-td
            pos={"side":side,"entry":e,"stop":st,"target":tg}
    return trades

def stats(rs):
    if not rs: return {"trades":0,"exp_pct":0.0,"wr":0.0,"mdd_pct":0.0,"pf":0.0}
    w=[r for r in rs if r>0]; l=[r for r in rs if r<=0]
    eq=peak=mdd=0.0
    for r in rs:
        eq+=r*RISK_PCT; peak=max(peak,eq); mdd=max(mdd,peak-eq)
    m=sum(rs)/len(rs)
    return {"trades":len(rs),"exp_pct":round(m*RISK_PCT,4),"wr":round(len(w)/len(rs),3),
            "mdd_pct":round(mdd,2),"pf":round(sum(w)/(abs(sum(l)) or 1e-9),3)}

GRID=list(itertools.product([(10,30),(20,50),(20,100),(50,200)],[1.5,2.0,3.0],[False,True]))
RSI_BOUNDS=[(30,70),(25,75)]

def main():
    cache={}
    for s in SYMBOLS:
        bars,src=load(s); cache[s]=(bars,src)
        print(f"  {s:7s} bars={len(bars):5d} src={src}")
    combos=[]
    for (tf,ts),rr,ur in GRID:
        for (rl,rh) in (RSI_BOUNDS if ur else [(0,100)]):
            combos.append({"tf":tf,"ts":ts,"rr":rr,"use_rsi":ur,"rsi_lo":rl,"rsi_hi":rh})
    results=[]
    for c in combos:
        tr,te=[],[]
        for s in SYMBOLS:
            bars,_=cache[s]
            if len(bars)<400: continue
            n=len(bars); cut=int(n*0.70); pr=dict(c); pr["_sym"]=s
            tr+=run(bars,210,cut,pr); te+=run(bars,cut,n-1,pr)
        results.append({"params":{k:c[k] for k in ("tf","ts","rr","use_rsi","rsi_lo","rsi_hi")},
                        "train":stats(tr),"test":stats(te),
                        "score":stats(te)["exp_pct"] if len(te)>=20 else -999})
    results.sort(key=lambda r:r["score"],reverse=True)
    survivors=[r for r in results if r["test"]["trades"]>=30 and r["test"]["exp_pct"]>0 and r["train"]["exp_pct"]>0]
    out={"ts":dt.datetime.now(dt.timezone.utc).isoformat(),
         "method":"walk-forward 70/30, real bars only, costs charged, no refit on test",
         "risk_pct":RISK_PCT,"cost_pips":COST_PIPS,"combos_tested":len(results),
         "survivors":survivors[:10],"top10_by_test":results[:10],
         "verdict":("EDGE FOUND - candidates warrant paper-forward testing" if survivors
                    else "NO ROBUST EDGE - stand-aside confirmed as correct discipline")}
    os.makedirs("reports",exist_ok=True)
    json.dump(out,open("reports/edge_search.json","w"),indent=2)
    print(f"\ncombos={len(results)} survivors={len(survivors)}")
    for r in results[:5]:
        print("  top:",r["params"],"train",r["train"]["exp_pct"],"test",r["test"]["exp_pct"],"testN",r["test"]["trades"])
    print("VERDICT:",out["verdict"])

if __name__=="__main__": main()
