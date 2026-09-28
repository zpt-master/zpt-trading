"""Grid-search strategy families on CACHED data with train/test split.
Reads cache/*.json, writes logs/optimizer.json. Run detached."""
import sys, json, itertools, glob, os
sys.path.insert(0,'/home/oroth/trading')
from indicators import ema, rsi, atr, adx

def simulate(cs, entries, rr, stop_mult, i0, max_bars=200):
    a=atr(cs,14); off=len(cs)-len(a); R=[]; i=i0
    while i < len(cs)-1:
        side=entries(cs,i)
        if not side: i+=1; continue
        ai=i-off
        if ai<0: i+=1; continue
        d=1.5*a[ai]*stop_mult; entry=cs[i]["c"]
        sl,tp=(entry-d,entry+d*rr) if side=="buy" else (entry+d,entry-d*rr)
        done=False
        for j in range(i+1,min(i+max_bars,len(cs))):
            h,l=cs[j]["h"],cs[j]["l"]
            if side=="buy":
                if l<=sl: R.append(-1.0); done=True; break
                if h>=tp: R.append(rr); done=True; break
            else:
                if h>=sl: R.append(-1.0); done=True; break
                if l<=tp: R.append(rr); done=True; break
        i=j if done else i+1
    return R

def stats(R):
    if len(R)<10: return None
    eq=1.0;peak=1.0;mdd=0.0
    for r in R: eq*=(1+0.01*r); peak=max(peak,eq); mdd=min(mdd,eq/peak-1)
    return {"n":len(R),"wr":round(sum(1 for x in R if x>0)/len(R),3),
            "avgR":round(sum(R)/len(R),3),"ret":round((eq-1)*100,2),"dd":round(mdd*100,2)}

def e_ema(fast,slow):
    def e(cs,i):
        if i<slow+2: return None
        c=[x["c"] for x in cs[:i+1]]; ef,es=ema(c,fast),ema(c,slow)
        if len(ef)<2 or len(es)<2: return None
        if ef[-2]<=es[-2] and ef[-1]>es[-1]: return "buy"
        if ef[-2]>=es[-2] and ef[-1]<es[-1]: return "sell"
    return e
def e_mr(lo,hi):
    def e(cs,i):
        if i<20: return None
        r=rsi([x["c"] for x in cs[:i+1]],14)
        if not r: return None
        if r[-1]<lo: return "buy"
        if r[-1]>hi: return "sell"
    return e
def e_don(look):
    def e(cs,i):
        if i<look+1: return None
        hi=max(x["h"] for x in cs[i-look:i]); lo=min(x["l"] for x in cs[i-look:i])
        if cs[i]["c"]>hi: return "buy"
        if cs[i]["c"]<lo: return "sell"
    return e
def e_rsi_trend(fast,slow,lo,hi):
    def e(cs,i):
        if i<slow+2: return None
        c=[x["c"] for x in cs[:i+1]]; ef,es=ema(c,fast),ema(c,slow); r=rsi(c,14)
        if not ef or not es or not r: return None
        if ef[-1]>es[-1] and r[-1]<lo: return "buy"
        if ef[-1]<es[-1] and r[-1]>hi: return "sell"
    return e
def e_adx_trend(fast,slow,thr):
    def e(cs,i):
        if i<slow+2: return None
        c=[x["c"] for x in cs[:i+1]]; ef,es=ema(c,fast),ema(c,slow); ax=adx(cs[:i+1],14)
        if not ef or not es or not ax or ax[-1]<thr: return None
        if ef[-1]>es[-1]: return "buy"
        if ef[-1]<es[-1]: return "sell"
    return e

FAM={"ema_9_21":e_ema(9,21),"ema_21_55":e_ema(21,55),"ema_50_200":e_ema(50,200),
     "mr_30_70":e_mr(30,70),"mr_25_75":e_mr(25,75),"mr_20_80":e_mr(20,80),
     "don_20":e_don(20),"don_55":e_don(55),"don_100":e_don(100),
     "rsi_t_21_55":e_rsi_trend(21,55,35,65),"rsi_t_50_200":e_rsi_trend(50,200,30,70),
     "adx_ema":e_adx_trend(21,55,25)}
RR=[1.0,1.5,2.0,3.0]; SM=[1.0,1.5,2.0,3.0]

files=sorted(glob.glob("cache/*_1h.json"))+sorted(glob.glob("cache/*_1d.json"))
res=[]
for f in files:
    sym=os.path.basename(f).split("_")[0]; itv=os.path.basename(f).split("_")[1].replace(".json","")
    cs=json.load(open(f))
    split=int(len(cs)*0.7)
    te=cs[split-260:]
    for name,ent in FAM.items():
        for rr,sm in itertools.product(RR,SM):
            Rte=simulate(te,ent,rr,sm,260)
            st=stats(Rte)
            if st and st["n"]>=12:
                res.append({"sym":sym,"itv":itv,"fam":name,"rr":rr,"sm":sm,**st})
json.dump(res,open("logs/optimizer.json","w"),indent=2)
res.sort(key=lambda r:r["avgR"],reverse=True)
pos=[r for r in res if r["avgR"]>0.05 and r["n"]>=15]
lines=[f"configs>=12 OOS trades: {len(res)}",f"net-positive (avgR>0.05,n>=15): {len(pos)}","",
       f"{'SYM':8}{'ITV':4}{'FAM':14}{'RR':>4}{'SM':>4}{'n':>5}{'WR':>7}{'avgR':>8}{'ret%':>8}{'dd%':>7}"]
for r in res[:40]:
    lines.append(f"{r['sym']:8}{r['itv']:4}{r['fam']:14}{r['rr']:>4}{r['sm']:>4}{r['n']:>5}{r['wr']:>7}{r['avgR']:>8}{r['ret']:>8}{r['dd']:>7}")
open("logs/optimizer.txt","w").write("\n".join(lines)+"\n")
print("DONE", len(res), "configs,", len(pos), "positive")
