"""Trend-following strategy (EMA cross + RSI filter + ATR stops).
Deliberately simple and conservative: no martingale, no averaging down."""
from indicators import ema, rsi, atr

def signal(cs, fast=20, slow=50, rsi_n=14):
    """Returns dict(side, reason, sl_dist, price) or None."""
    closes = [c["c"] for c in cs]
    if len(closes) < slow + 5:
        return None
    ef, es = ema(closes, fast), ema(closes, slow)
    if not ef or not es: return None
    # align: both end at same index
    n = min(len(ef), len(es))
    ef, es = ef[-n:], es[-n:]
    r = rsi(closes, rsi_n)
    a = atr(cs, 14)
    if len(r) < 2 or not a: return None
    price = closes[-1]
    a_now = a[-1]
    # crossover in the last completed bar
    up = ef[-2] <= es[-2] and ef[-1] > es[-1]
    dn = ef[-2] >= es[-2] and ef[-1] < es[-1]

    if up and r[-1] < 70:
        return {"side": "buy", "reason": f"EMA{fast}>{slow} cross, RSI {r[-1]:.0f}",
                "sl_dist": 1.5 * a_now, "price": price}
    if dn and r[-1] > 30:
        return {"side": "sell", "reason": f"EMA{fast}<{slow} cross, RSI {r[-1]:.0f}",
                "sl_dist": 1.5 * a_now, "price": price}
    return None

def levels(side, price, sl_dist, rr=1.5):
    if side == "buy":
        return price - sl_dist, price + sl_dist * rr
    return price + sl_dist, price - sl_dist * rr
