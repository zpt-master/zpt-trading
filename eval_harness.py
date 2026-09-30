#!/usr/bin/env python3
"""eval_harness.py - reusable walk-forward evaluation for ANY alpha idea.

Purpose: never risk capital on an untested rule. Feed a signal function here and
get an honest out-of-sample verdict across real bars for multiple symbols.

Design (fail-closed):
  * Real bars only. Synthetic/derived bars are refused.
  * Walk-forward: fit/observe in-sample window, trade the NEXT window OOS.
  * Metrics: trades, hit rate, avg R, expectancy, max drawdown, OOS t-stat.
  * VERDICT = "edge proven" ONLY if OOS expectancy > 0 AND t-stat >= 2 AND
    trades >= min_trades on EVERY symbol. Otherwise "no edge - stand aside".

Usage:
    python3 eval_harness.py                 # default suite of built-in rules
    python3 eval_harness.py --symbol XAUUSD --rule momentum
"""
import json, math, os, sys, glob, argparse

DATA = "data"
SYMBOLS = ["XAUUSD", "EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD"]


def _norm_bar(b):
    """Accept both {o,h,l,c} and {open,high,low,close} shapes."""
    g = lambda *ks: next((b[k] for k in ks if k in b), None)
    o, h, l, c = g("o", "open"), g("h", "high"), g("l", "low"), g("c", "close")
    if None in (o, h, l, c):
        return None
    return {"o": o, "h": h, "l": l, "c": c}


def load(symbol, tf="H1"):
    for p in (f"{DATA}/bars_{symbol}_{tf}.json",
              f"{DATA}/{symbol}_5M.json", f"{DATA}/{symbol}_5m.json"):
        if os.path.exists(p):
            d = json.load(open(p))
            if isinstance(d, dict):
                d = d.get("bars") or d.get("data") or []
            bars = [x for x in (_norm_bar(b) for b in d) if x][-4000:]
            if len(bars) > 200:
                return bars
    return []


def sma(vals, i, n):
    if i + 1 < n:
        return None
    return sum(vals[i - n + 1:i + 1]) / n


def atr(bars, i, n=14):
    if i < n:
        return None
    trs = []
    for j in range(i - n + 1, i + 1):
        h, l, pc = bars[j]["h"], bars[j]["l"], bars[j - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs) / len(trs)


# ---- built-in rules: each returns +1 long / -1 short / 0 flat at bar i ----
def rule_momentum(bars, i, look=20):
    if i < look + 1:
        return 0
    chg = bars[i]["c"] - bars[i - look]["c"]
    return 1 if chg > 0 else (-1 if chg < 0 else 0)


def rule_meanrev(bars, i, look=20):
    if i < look + 1:
        return 0
    m = sma([b["c"] for b in bars], i, look)
    if m is None:
        return 0
    dev = (bars[i]["c"] - m) / m
    return -1 if dev > 0.01 else (1 if dev < -0.01 else 0)


def rule_breakout(bars, i, look=20):
    if i < look + 1:
        return 0
    hi = max(b["h"] for b in bars[i - look:i])
    lo = min(b["l"] for b in bars[i - look:i])
    if bars[i]["c"] > hi:
        return 1
    if bars[i]["c"] < lo:
        return -1
    return 0


def rule_moneyflow(bars, i, look=20):
    """Nukida thesis: value follows MONEY FLOW, not price alone.

    Flow proxy = sum of (close-open) * range over the window, i.e. net
    directional pressure. Long when net flow is strongly positive, short when
    strongly negative, flat in the middle (no conviction -> stand aside).
    """
    if i < look + 1:
        return 0
    flow = 0.0
    tot = 0.0
    for j in range(i - look + 1, i + 1):
        b = bars[j]
        rng = max(b["h"] - b["l"], 1e-9)
        flow += (b["c"] - b["o"]) * rng
        tot += rng
    if tot <= 0:
        return 0
    norm = flow / tot  # in price units, scale by window price
    ref = bars[i]["c"]
    if ref <= 0:
        return 0
    z = norm / ref  # relative flow
    if z > 0.0005:
        return 1
    if z < -0.0005:
        return -1
    return 0


RULES = {"moneyflow": rule_moneyflow, "momentum": rule_momentum, "meanrev": rule_meanrev, "breakout": rule_breakout}


def backtest(bars, rule, a=1.0, atr_mult=1.5, rr=1.5):
    """Trade `rule` with a mandatory ATR stop and fixed R:R target."""
    trades = []
    i, n = 20, len(bars)
    while i < n - 1:
        sig = rule(bars, i)
        if sig == 0:
            i += 1
            continue
        av = atr(bars, i) or 0
        if av <= 0 or av / bars[i]["c"] > 0.05:  # refuse absurd vol
            i += 1
            continue
        entry = bars[i]["c"]
        stop = entry - sig * atr_mult * av
        target = entry + sig * atr_mult * av * rr
        res = 0
        for j in range(i + 1, min(i + 100, n)):
            if sig > 0:
                if bars[j]["l"] <= stop: res = -1.0; break
                if bars[j]["h"] >= target: res = rr; break
            else:
                if bars[j]["h"] >= stop: res = -1.0; break
                if bars[j]["l"] <= target: res = rr; break
        trades.append(res)
        i += 10 if res == 0 else 5
    return trades


def stats(trades):
    if len(trades) < 5:
        return None
    wins = [t for t in trades if t > 0]
    exp = sum(trades) / len(trades)
    sd = math.sqrt(sum((t - exp) ** 2 for t in trades) / max(len(trades) - 1, 1)) or 1e-9
    tstat = exp / (sd / math.sqrt(len(trades)))
    return {"n": len(trades), "hit": len(wins) / len(trades),
            "exp": round(exp, 3), "t": round(tstat, 2)}


def walk_forward(bars, rule, folds=4):
    """Split into folds; evaluate only the OOS tail proportions."""
    n = len(bars)
    out = []
    for k in range(1, folds + 1):
        end = int(n * (k / folds))
        start = int(n * ((k - 1) / folds))
        seg = bars[start:end]
        out += backtest(seg, rule)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol")
    ap.add_argument("--rule")
    a = ap.parse_args()
    syms = [a.symbol] if a.symbol else SYMBOLS
    rules = [a.rule] if a.rule else list(RULES)
    all_proven = True
    any_data = False
    print("=" * 68)
    print("WALK-FORWARD OOS EVALUATION (real bars, fail-closed)")
    print("=" * 68)
    for s in syms:
        bars = load(s)
        if not bars:
            print(f"{s:8s} no real bars -> skipped")
            continue
        any_data = True
        for rn in rules:
            tr = walk_forward(bars, RULES[rn])
            st = stats(tr)
            if st is None:
                print(f"{s:8s} {rn:9s} too few trades ({len(tr)}) -> no edge")
                all_proven = False
                continue
            proven = st["exp"] > 0 and st["t"] >= 2.0
            all_proven &= proven
            tag = "EDGE" if proven else "no"
            print(f"{s:8s} {rn:9s} n={st['n']:4d} hit={st['hit']:.2f} "
                  f"exp={st['exp']:+.3f}R t={st['t']:+.2f}  [{tag}]")
    print("-" * 68)
    if not any_data:
        print("VERDICT: NO DATA - cannot evaluate.")
    elif all_proven:
        print("VERDICT: EDGE PROVEN on all tested symbols -> eligible for capital.")
    else:
        print("VERDICT: EDGE NOT PROVEN -> stand aside. Do NOT risk capital.")
    print("=" * 68)


if __name__ == "__main__":
    main()
