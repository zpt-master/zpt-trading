"""Risk-aware actionable summary."""
from .indicators import ema, rsi, atr, adx
from .regime import classify

MAX_RISK_PCT = 2.0  # per-trade, of account equity

def summarize(symbol, candles, account_equity=None):
    if not candles or len(candles) < 30:
        return {"symbol":symbol,"error":"insufficient_data","n":len(candles or [])}
    c=[x["c"] for x in candles]
    price=c[-1]
    e21, e50 = ema(c,21)[-1], ema(c,50)[-1]
    e200 = ema(c,200)[-1] if len(c)>=200 else None
    rv, av, tv = rsi(c,14)[-1], adx(candles,14)[-1], atr(candles,14)[-1]
    reg = classify(price, e21, e50, e200, rv, av, tv)
    out = {"symbol":symbol,"price":round(price,5),"rsi":round(rv,1),
           "adx":round(av,1) if av is not None else None,
           "atr":round(tv,5) if tv is not None else None, **reg}
    if tv is not None:
        stop = price - 1.5*tv if reg["trend"]=="up" else price + 1.5*tv
        out["stop"] = round(stop,5)
        if account_equity and tv:
            risk_usd = account_equity * MAX_RISK_PCT/100
            out["max_risk_usd"] = round(risk_usd,2)
            out["note"] = "cap size so stop loss <= max_risk_usd"
    out["actionable"] = (reg["conviction"] in ("moderate","trending")
                         and 35 < rv < 65 and reg["trend"]!="range")
    return out
