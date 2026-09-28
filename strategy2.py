"""Strategy v2: trade WITH the higher-timeframe trend, enter on pullback
momentum, require trending regime (ADX). Targets fewer, higher-quality entries."""
from indicators import ema, rsi, atr, adx

def signal(cs, fast=21, slow=55, trend=200, rsi_n=14):
    closes=[c["c"] for c in cs]
    if len(closes) < trend + 10: return None
    ef,es = ema(closes,fast), ema(closes,slow)
    et = ema(closes,trend)
    if not ef or not es or not et: return None
    n=min(len(ef),len(es),len(et)); ef,es,et=ef[-n:],es[-n:],et[-n:]
    r=rsi(closes,rsi_n); a=atr(cs,14); ax=adx(cs,14)
    if len(r)<2 or not a or not ax: return None
    price=closes[-1]; a_now=a[-1]; adx_now=ax[-1]
    if adx_now < 25: return None                       # require a trending regime
    trend_up = ef[-1] > es[-1] and price > et[-1]
    trend_dn = ef[-1] < es[-1] and price < et[-1]
    # pullback + momentum resumption: RSI dipped then turns, price back above fast EMA
    up = trend_up and r[-2] < 50 and r[-1] > r[-2] and price > ef[-1]
    dn = trend_dn and r[-2] > 50 and r[-1] < r[-2] and price < ef[-1]
    if up: return {"side":"buy","reason":f"trend-up pullback RSI{r[-1]:.0f} ADX{adx_now:.0f}","sl_dist":1.5*a_now,"price":price}
    if dn: return {"side":"sell","reason":f"trend-dn pullback RSI{r[-1]:.0f} ADX{adx_now:.0f}","sl_dist":1.5*a_now,"price":price}
    return None

def levels(side, price, sl_dist, rr=1.5):
    return (price-sl_dist, price+sl_dist*rr) if side=="buy" else (price+sl_dist, price-sl_dist*rr)
