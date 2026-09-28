"""
moneyflow.py - Nukida-inspired MONEY FLOW intelligence.
Thesis (nukida.co): an asset's value is set by capital FLOW, not by chart
shapes or news. This module quantifies flow from OHLCV bars:

  - MFI (Money Flow Index, 14): volume-weighted RSI
  - CMF (Chaikin Money Flow, 20): accumulation/distribution pressure
  - Relative Volume (RVOL): volume vs 20-bar average (conviction)
  - Flow regime: ACCUMULATION / DISTRIBUTION / NEUTRAL / CLIMAX
  - flow_score: -100..+100 composite

Dependency-free. Works on bars that expose o,h,l,c,v (dicts or attrs).
"""
def _v(b):
    for k in ("v","volume"):
        try:
            if isinstance(b, dict) and k in b: return float(b[k] or 0)
            x = getattr(b, k, None)
            if x is not None: return float(x)
        except Exception: pass
    return 0.0
def _activity(bars):
    """Return (vol_series, source). Uses real volume if present in EVERY bar;
    otherwise a transparent activity PROXY = high-low range * close
    (larger ranges on higher prices = more activity). Documented, not hidden."""
    real=[_v(b) for b in bars]
    if any(x>0 for x in real):
        return real,"volume"
    prox=[]
    for b in bars:
        h,l,c=_g(b,"h"),_g(b,"l"),_g(b,"c")
        prox.append(max(0.0,(h-l))*max(c,1e-9))
    return prox,"range_proxy"

def _g(b,k):
    try:
        return float(b[k]) if isinstance(b,dict) else float(getattr(b,k))
    except Exception:
        return 0.0

def money_flow_index(bars, n=14):
    if len(bars) < n+1: return None
    act,_=_activity(bars)
    pos=neg=0.0
    for i in range(1, n+1):
        tp_now=(_g(bars[-i],"h")+_g(bars[-i],"l")+_g(bars[-i],"c"))/3
        tp_prev=(_g(bars[-i-1],"h")+_g(bars[-i-1],"l")+_g(bars[-i-1],"c"))/3
        flow=tp_now*act[-i]
        if tp_now>tp_prev: pos+=flow
        elif tp_now<tp_prev: neg+=flow
    if neg==0: return 100.0 if pos>0 else 50.0
    mr=pos/neg
    return 100 - (100/(1+mr))

def chaikin_money_flow(bars, n=20):
    if len(bars) < n: return None
    act,_=_activity(bars)
    mfv=vol=0.0
    for b,a in zip(bars[-n:],act[-n:]):
        h,l,c,v=_g(b,"h"),_g(b,"l"),_g(b,"c"),a
        rng=h-l
        mfm=0.0 if rng==0 else ((c-l)-(h-c))/rng
        mfv+=mfm*v; vol+=v
    return None if vol==0 else mfv/vol

def relative_volume(bars, n=20):
    if len(bars) < n+1: return None
    act,_=_activity(bars)
    avg=sum(act[-(n+1):-1])/n
    if avg<=0: return None
    return act[-1]/avg

def flow_regime(mfi, cmf, rvol):
    if mfi is None or cmf is None:
        return "UNKNOWN"
    if mfi>=80 and (rvol or 1)>=2: return "CLIMAX_UP"
    if mfi<=20 and (rvol or 1)>=2: return "CLIMAX_DOWN"
    if cmf>0.05 and mfi>=55: return "ACCUMULATION"
    if cmf<-0.05 and mfi<=45: return "DISTRIBUTION"
    return "NEUTRAL"

def flow_score(mfi, cmf, rvol):
    if mfi is None or cmf is None: return 0
    s=0.0
    s += (mfi-50)*1.0           # -50..+50
    s += max(-30,min(30, cmf*300))  # cmf +/-0.1 -> +/-30
    if rvol is not None:
        s += max(-20,min(20,(rvol-1)*20))  # conviction bonus
    return int(max(-100,min(100,s)))

def _clean(bars):
    """Drop a trailing degenerate bar (h==l, e.g. a just-opened live candle)."""
    if len(bars)>=2:
        b=bars[-1]; h,l=_g(b,"h"),_g(b,"l")
        if h==l: return bars[:-1]
    return bars

def analyze(bars):
    bars=_clean(bars)
    _,vsrc=_activity(bars)
    mfi=money_flow_index(bars); cmf=chaikin_money_flow(bars); rv=relative_volume(bars)
    reg=flow_regime(mfi,cmf,rv); sc=flow_score(mfi,cmf,rv)
    return {
        "mfi": None if mfi is None else round(mfi,1),
        "cmf": None if cmf is None else round(cmf,4),
        "rvol": None if rv is None else round(rv,2),
        "flow_regime": reg,
        "flow_score": sc,
        "volume_source": vsrc,
        "read": _read(reg,sc),
    }

def _read(reg,sc):
    base={
     "ACCUMULATION":"Capital flowing IN - buyers in control.",
     "DISTRIBUTION":"Capital flowing OUT - sellers in control.",
     "CLIMAX_UP":"Volume climax on the buy side - late-stage / exhaustion risk.",
     "CLIMAX_DOWN":"Volume climax on the sell side - capitulation / reversal watch.",
     "NEUTRAL":"No decisive capital flow - range / wait.",
     "UNKNOWN":"Insufficient data.",
    }.get(reg,"")
    if sc>=40: base+=" Bias: long-side flow."
    elif sc<=-40: base+=" Bias: short-side flow."
    return base

if __name__=="__main__":
    import sys,json
    sys.path.insert(0,".")
    try:
        import feed
        cs=feed.candles("EURUSD",interval="1h",rng="10d")
        print(json.dumps(analyze(cs),indent=2))
    except Exception as e:
        print("need live feed:",e)
