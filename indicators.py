"""Pure-python indicators. No numpy/pandas needed."""
def ema(vals, n):
    if len(vals) < n: return []
    k = 2/(n+1); out=[sum(vals[:n])/n]
    for v in vals[n:]: out.append(v*k + out[-1]*(1-k))
    return out
def sma(vals,n):
    return [sum(vals[i-n:i])/n for i in range(n,len(vals)+1)] if len(vals)>=n else []
def rsi(vals, n=14):
    if len(vals)<=n: return []
    g=l=0.0
    for i in range(1,n+1):
        d=vals[i]-vals[i-1]; g+=max(d,0); l+=max(-d,0)
    ag,al=g/n,l/n; out=[]
    for i in range(n+1,len(vals)):
        d=vals[i]-vals[i-1]; ag=(ag*(n-1)+max(d,0))/n; al=(al*(n-1)+max(-d,0))/n
        out.append(100-100/(1+(ag/al if al else 999)))
    return out
def atr(cs,n=14):
    trs=[max(cs[i]["h"]-cs[i]["l"],abs(cs[i]["h"]-cs[i-1]["c"]),abs(cs[i]["l"]-cs[i-1]["c"])) for i in range(1,len(cs))]
    if len(trs)<n: return []
    out=[sum(trs[:n])/n]
    for tr in trs[n:]: out.append((out[-1]*(n-1)+tr)/n)
    return out
def adx(cs,n=14):
    """Wilder ADX — trend strength. >25 = trending, <20 = ranging."""
    if len(cs)<2*n: return []
    tr=[];pdm=[];ndm=[]
    for i in range(1,len(cs)):
        up=cs[i]["h"]-cs[i-1]["h"]; dn=cs[i-1]["l"]-cs[i]["l"]
        pdm.append(up if (up>dn and up>0) else 0.0)
        ndm.append(dn if (dn>up and dn>0) else 0.0)
        tr.append(max(cs[i]["h"]-cs[i]["l"],abs(cs[i]["h"]-cs[i-1]["c"]),abs(cs[i]["l"]-cs[i-1]["c"])))
    def wilder(x):
        o=[sum(x[:n])]
        for v in x[n:]: o.append(o[-1]-o[-1]/n+v)
        return o
    atr_=wilder(tr); pdm_=wilder(pdm); ndm_=wilder(ndm)
    dx=[]
    for i in range(len(atr_)):
        p=100*pdm_[i]/atr_[i] if atr_[i] else 0; m=100*ndm_[i]/atr_[i] if atr_[i] else 0
        dx.append(100*abs(p-m)/(p+m) if (p+m) else 0)
    if len(dx)<n: return []
    adx_=sum(dx[:n])/n; out=[adx_]
    for v in dx[n:]: adx_=(adx_*(n-1)+v)/n; out.append(adx_)
    return out
