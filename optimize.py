"""Grid-search multiple strategy families with walk-forward train/test split.
Goal: find edge that survives OUT-OF-SAMPLE. Honest: report everything."""
import sys, json, itertools; sys.path.insert(0,'/home/oroth/trading')
import feed
from indicators import ema, rsi, atr, adx

def simulate(cs, entries, rr, stop_mult, atr_win=14, max_bars=200, i0=0):
    """entries: function(cs, i)-> 'buy'|'sell'|None. Returns list of R multiples."""
    a = atr(cs, atr_win)
    off = len(cs) - len(a)                      # a[i-off] aligns with cs[i]
    R=[]
    i=i0
    while i < len(cs)-1:
        side = entries(cs, i)
        if not side: i+=1; continue
        ai = i-off
        if ai<0: i+=1; continue
        d = 1.5*a[ai]*stop_mult
        entry=cs[i]["c"]
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
        i = j if done else i+1
    return R

def stats(R):
    if len(R)<10: return None
    eq=1.0;peak=1.0;mdd=0.0
    for r in R:
        eq*=(1+0.01*r); peak=max(peak,eq); mdd=min(mdd,eq/peak-1)
    return {"n":len(R),"wr":round(sum(1 for x in R if x>0)/len(R),3),
            "avgR":round(sum(R)/len(R),3),"ret":round((eq-1)*100,2),"dd":round(mdd*100,2)}

# ---- strategy families (entry fn factory) ----
def f_ema_cross(fast,slow):
    def e(cs,i):
        if i<slow+2: return None
        c=[x["c"] for x in cs[:i+1]]
        ef,es=ema(c,fast),ema(c,slow)
        if len(ef)<2 or len(es)<2: return None
        if ef[-2]<=es[-2] and ef[-1]>es[-1]: return "buy"
        if ef[-2]>=es[-2] and ef[-1]<es[-1]: return "sell"
        return None
    return e

def f_meanrev(lo,hi):
    """Fade RSI extremes — often stronger on FX ranges."""
    def e(cs,i):
        if i<20: return None
        c=[x["c"] for x in cs[:i+1]]
        r=rsi(c,14)
        if len(r)<1: return None
        if r[-1]<lo: return "buy"
        if r[-1]>hi: return "sell"
        return None
    return e

def f_donchian(look):
    """Breakout of N-bar high/low (trend)."""
    def e(cs,i):
        if i<look+1: return None
        hi=max(x["h"] for x in cs[i-look:i]); lo=min(x["l"] for x in cs[i-look:i])
        c=cs[i]["c"]
        if c>hi: return "buy"
        if c<lo: return "sell"
        return None
    return e

def f_rsi_trend(fast,slow,lo,hi):
    """Trade with EMA trend, enter on RSI pullback."""
    def e(cs,i):
        if i<slow+2: return None
        c=[x["c"] for x in cs[:i+1]]
        ef,es=ema(c,fast),ema(c,slow); r=rsi(c,14)
        if not ef or not es or not r: return None
        if ef[-1]>es[-1] and r[-1]<lo: return "buy"
        if ef[-1]<es[-1] and r[-1]>hi: return "sell"
        return None
    return e

FAMILIES={
 "ema_9_21":   f_ema_cross(9,21),
 "ema_21_55":  f_ema_cross(21,55),
 "meanrev_30_70": f_meanrev(30,70),
 "meanrev_25_75": f_meanrev(25,75),
 "meanrev_20_80": f_meanrev(20,80),
 "donchian_20": f_donchian(20),
 "donchian_55": f_donchian(55),
 "rsi_trend_21_55": f_rsi_trend(21,55,35,65),
 "rsi_trend_50_200": f_rsi_trend(50,200,30,70),
}

SYMS=["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","XAUUSD"]
RR=[1.0,1.5,2.0,3.0]; SM=[1.0,2.0,3.0]

data={s:feed.candles(s,"1h","2y") for s in SYMS}
results=[]
for name,ent in FAMILIES.items():
    for rr,sm in itertools.product(RR,SM):
        for s in SYMS:
            cs=data[s]; split=int(len(cs)*0.7)
            Rin=simulate(cs,ent,rr,sm,i0=260)                      # full
            Rtr=simulate(cs[:split],ent,rr,sm,i0=260)              # in-sample
            # out-of-sample: re-run on test slice with warmup
            cs_te=cs[split-260:]
            Rte=simulate(cs_te,ent,rr,sm,i0=260)
            st=stats(Rte)
            if st and st["n"]>=12:
                results.append({"fam":name,"rr":rr,"sm":sm,"sym":s,**st})
json.dump(results,open("logs/optimizer.json","w"),indent=2)
results.sort(key=lambda r:r["avgR"], reverse=True)
print(f"total configs with >=12 OOS trades: {len(results)}")
print(f"\n{'FAM':18}{'RR':>4}{'SM':>4}{'SYM':>8}{'n':>4}{'WR':>7}{'avgR':>8}{'ret%':>8}{'dd%':>7}")
for r in results[:20]:
    print(f"{r['fam']:18}{r['rr']:>4}{r['sm']:>4}{r['sym']:>8}{r['n']:>4}{r['wr']:>7}{r['avgR']:>8}{r['ret']:>8}{r['dd']:>7}")
pos=[r for r in results if r["avgR"]>0.05 and r["n"]>=15]
print(f"\nNET-POSITIVE OOS configs (avgR>0.05, n>=15): {len(pos)}")
for r in pos[:12]: print(f"  {r['fam']:18}{r['rr']:>4}{r['sm']:>4}{r['sym']:>8} n={r['n']} wr={r['wr']} avgR={r['avgR']} ret%={r['ret']}")
