"""Shared simulate/stats/strategy-family definitions."""
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

FAMILIES={"ema_9_21":e_ema(9,21),"ema_21_55":e_ema(21,55),"ema_50_200":e_ema(50,200),
 "mr_30_70":e_mr(30,70),"mr_25_75":e_mr(25,75),"mr_20_80":e_mr(20,80),
 "don_20":e_don(20),"don_55":e_don(55),"don_100":e_don(100),
 "rsi_t_21_55":e_rsi_trend(21,55,35,65),"rsi_t_50_200":e_rsi_trend(50,200,30,70)}
