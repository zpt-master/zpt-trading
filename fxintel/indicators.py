"""Indicators. Lists in, lists out. No deps."""
def sma(x, n):
    out=[None]*len(x)
    for i in range(n-1, len(x)):
        out[i]=sum(x[i-n+1:i+1])/n
    return out

def ema(x, n):
    out=[None]*len(x); k=2/(n+1)
    if len(x) < n: return out
    s=sum(x[:n])/n; out[n-1]=s
    for i in range(n, len(x)):
        s=x[i]*k + s*(1-k); out[i]=s
    return out

def rsi(x, n=14):
    out=[None]*len(x)
    if len(x) <= n: return out
    gains=[0]*len(x); losses=[0]*len(x)
    for i in range(1,len(x)):
        d=x[i]-x[i-1]
        gains[i]=max(d,0); losses[i]=max(-d,0)
    ag=sum(gains[1:n+1])/n; al=sum(losses[1:n+1])/n
    out[n]=100 if al==0 else 100-100/(1+ag/al)
    for i in range(n+1,len(x)):
        ag=(ag*(n-1)+gains[i])/n; al=(al*(n-1)+losses[i])/n
        out[i]=100 if al==0 else 100-100/(1+ag/al)
    return out

def atr(candles, n=14):
    if len(candles) < n+1: return [None]*len(candles)
    tr=[None]*len(candles)
    for i in range(1,len(candles)):
        h=candles[i]["h"]; l=candles[i]["l"]; pc=candles[i-1]["c"]
        tr[i]=max(h-l, abs(h-pc), abs(l-pc))
    out=[None]*len(candles)
    a=sum(tr[1:n+1])/n; out[n]=a
    for i in range(n+1,len(candles)):
        a=(a*(n-1)+tr[i])/n; out[i]=a
    return out

def adx(candles, n=14):
    out=[None]*len(candles)
    if len(candles) < 2*n+1: return out
    pdm=[0]*len(candles); ndm=[0]*len(candles); tr=[0]*len(candles)
    for i in range(1,len(candles)):
        up=candles[i]["h"]-candles[i-1]["h"]
        dn=candles[i-1]["l"]-candles[i]["l"]
        pdm[i]=up if (up>dn and up>0) else 0
        ndm[i]=dn if (dn>up and dn>0) else 0
        h=candles[i]["h"]; l=candles[i]["l"]; pc=candles[i-1]["c"]
        tr[i]=max(h-l, abs(h-pc), abs(l-pc))
    def wilder(v):
        s=[None]*len(v); a=sum(v[1:n+1]); s[n]=a
        for i in range(n+1,len(v)):
            a=a-a/n+v[i]; s[i]=a
        return s
    str_=wilder(tr); spdm=wilder(pdm); sndm=wilder(ndm)
    dx=[None]*len(candles)
    for i in range(n,len(candles)):
        if not str_[i]: continue
        pdi=100*(spdm[i]/str_[i]); ndi=100*(sndm[i]/str_[i])
        dx[i]=100*abs(pdi-ndi)/(pdi+ndi) if (pdi+ndi) else 0
    start=2*n
    if start>=len(candles) or dx[start] is None: return out
    a=sum(d for d in dx[n:2*n+1] if d is not None)/n; out[2*n]=a
    for i in range(2*n+1,len(candles)):
        if dx[i] is None: continue
        a=(a*(n-1)+dx[i])/n; out[i]=a
    return out
