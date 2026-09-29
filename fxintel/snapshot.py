#!/usr/bin/env python3
"""snapshot.py — build the rich /intel payload from the real engine.

Per-symbol: price, regime, trend/flow, key indicators, and the risk-governed plan
(or FLAT with reason). Everything degrades gracefully; never raises.
"""
from __future__ import annotations
import json, os, time, traceback

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYMBOLS = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","USDCHF","NZDUSD","EURJPY","AUDJPY","XAUUSD"]

def _read(p):
    try: return open(os.path.join(HERE, p)).read()
    except Exception: return ""

def _num(x, nd=5):
    try: return round(float(x), nd)
    except Exception: return None

def _last(seq):
    try:
        if hasattr(seq, "__len__"): return seq[-1] if len(seq) else None
        return list(seq)[-1]
    except Exception: return None

def _rows(b):
    if isinstance(b, dict): b = b.get("bars") or b.get("candles") or []
    return b or []

def _closes(b):
    out=[]
    for c in _rows(b):
        v = c.get("close", c.get("c")) if isinstance(c, dict) else getattr(c, "close", None)
        if v is not None: out.append(float(v))
    return out

def _h(c): return c.get("h", c.get("high")) if isinstance(c,dict) else getattr(c,"high",None)
def _l(c): return c.get("l", c.get("low")) if isinstance(c,dict) else getattr(c,"low",None)
def _c(c): return c.get("c", c.get("close")) if isinstance(c,dict) else getattr(c,"close",None)
def _o(c): return c.get("o", c.get("open")) if isinstance(c,dict) else getattr(c,"open",None)

def _ohlc(b):
    out=[]
    for c in _rows(b):
        out.append({"h":_h(c),"l":_l(c),"c":_c(c),"o":_o(c),
                    "high":_h(c),"low":_l(c),"close":_c(c),"open":_o(c)})
    return out

def _one(symbol):
    out={"symbol":symbol}
    try:
        from fxintel import bars as B, indicators as I, regime as R, moneyflow as MF
        b = B.load(symbol,"H1",count=400,allow_synthetic=True)
        if isinstance(b, tuple): b=b[0]
        src = getattr(b,"source",None) or (b.get("source") if isinstance(b,dict) else None)
        try: out["source"] = "real" if (src and B.is_real(src)) else (src or "unknown")
        except Exception: out["source"] = src or "unknown"
        closes=_closes(b)
        if len(closes)<60: out["error"]="insufficient_bars"; return out
        price=closes[-1]
        e21=_last(I.ema(closes,21)); e50=_last(I.ema(closes,50)); e200=_last(I.ema(closes,200))
        rsi=_last(I.rsi(closes,14))
        adx=_last(I.adx(_ohlc(b),14)) if hasattr(I,"adx") else None
        atr=_last(I.atr(_ohlc(b),14)) if hasattr(I,"atr") else None
        out["price"]=_num(price)
        out["indicators"]={"ema21":_num(e21),"ema50":_num(e50),"ema200":_num(e200),
                           "rsi14":_num(rsi,2),"adx14":_num(adx,2),"atr14":_num(atr,5)}
        try:
            reg=R.classify(price,e21,e50,e200,rsi,adx,atr)
            out["regime"]=reg if isinstance(reg,(dict,str)) else str(reg)
        except Exception as e: out["regime"]={"error":str(e)[:80]}
        try:
            mf=MF.analyze(b)
            out["money_flow"]=({k:(_num(v,4) if isinstance(v,(int,float)) else v) for k,v in mf.items()}
                               if isinstance(mf,dict) else {"raw":str(mf)[:200]})
        except Exception as e: out["money_flow"]={"error":str(e)[:80]}
        try:
            from fxintel import signals as S
            plan=None
            for fn in ("build_plan","plan","build"):
                f=getattr(S,fn,None)
                if callable(f):
                    try: plan = f(symbol,b) if f.__code__.co_argcount>=2 else f(symbol)
                    except TypeError: plan = f(b)
                    break
            if isinstance(plan,dict):
                keep=("side","valid","entry","stop","target","rr","size_lots","risk_usd","confidence","rationale")
                out["plan"]={k:plan.get(k) for k in keep if k in plan}
            elif plan is not None: out["plan"]={"raw":str(plan)[:200]}
        except Exception as e: out["plan"]={"error":str(e)[:80]}
    except Exception as e:
        out["error"]=str(e)[:120]; out["trace"]=traceback.format_exc().splitlines()[-1][:160]
    return out

def build(symbols=None, include_news=True):
    syms=symbols or SYMBOLS
    data=[]
    for s in syms:
        try: data.append(_one(s))
        except Exception as e: data.append({"symbol":s,"error":str(e)[:120]})
    valid=[d for d in data if isinstance(d.get("plan"),dict) and d["plan"].get("valid")]
    payload={"service":"ZptMaster Intel","version":"2.0","ts":int(time.time()),
             "generated":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
             "discipline":{"max_risk_per_order_pct":1.5,"mandatory_stop":True,"martingale":False,
                           "rule":"trade only on aligned trend+flow conviction; otherwise FLAT"},
             "summary":{"symbols":len(data),"actionable":len(valid),"stand_aside":len(data)-len(valid)},
             "plans":data}
    if include_news: payload["news"]=_read("reports/news_digest.md")[:4000]
    return payload

if __name__=="__main__":
    d=build()
    print("summary:",json.dumps(d["summary"]))
    print("sample:",json.dumps(d["plans"][0])[:400])
