"""Pure-python indicators. No numpy/pandas needed."""

def ema(vals, n):
    if len(vals) < n: return []
    k = 2 / (n + 1)
    out = [sum(vals[:n]) / n]
    for v in vals[n:]:
        out.append(v * k + out[-1] * (1 - k))
    return out  # aligned to vals[n-1:]

def rsi(vals, n=14):
    if len(vals) <= n: return []
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = vals[i] - vals[i - 1]
        gains += max(d, 0); losses += max(-d, 0)
    ag, al = gains / n, losses / n
    out = []
    for i in range(n + 1, len(vals)):
        d = vals[i] - vals[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
        rs = ag / al if al else 999
        out.append(100 - 100 / (1 + rs))
    return out

def atr(cs, n=14):
    trs = []
    for i in range(1, len(cs)):
        h, l, pc = cs[i]["h"], cs[i]["l"], cs[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(trs) < n: return []
    out = [sum(trs[:n]) / n]
    for tr in trs[n:]:
        out.append((out[-1] * (n - 1) + tr) / n)
    return out
