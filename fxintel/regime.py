"""Regime classification from indicators."""
def classify(price, e21, e50, e200, rsi_v, adx_v, atr_v):
    if None in (e21, e50, rsi_v, adx_v):
        return {"trend":"unknown","bias":"unknown","conviction":"unknown"}
    if e200 is not None:
        if price>e50>e200: trend="up"
        elif price<e50<e200: trend="down"
        else: trend="range"
    else:
        trend = "up" if price>e21>e50 else "down" if price<e21<e50 else "range"
    bias = "overbought" if rsi_v>70 else "oversold" if rsi_v<30 else "neutral"
    conv = "low" if adx_v<20 else "moderate" if adx_v<25 else "trending"
    return {"trend":trend,"bias":bias,"conviction":conv}
