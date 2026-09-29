#!/usr/bin/env python3
"""xau/sweep.py - parameter sweep + walk-forward on REAL 2y M5 gold (PAXG).

Goal: find whether ANY risk-governed config of the XAUUSD scalp rule set is
profitable out-of-sample. Honest framing: we optimize on year 1, then test the
chosen config on year 2 (no lookahead). If nothing survives, we say so.

Rules kept identical to the EA: mandatory ATR stop, fixed RR, fixed-fractional
risk, daily<3% / weekly<5% gates, no martingale.
"""
import json, os, sys, math, itertools
import numpy as np

bars = json.load(open("data/XAUUSD_5m.json"))
T = np.array([b["t"] for b in bars], dtype=np.int64)
O = np.array([b["o"] for b in bars]); H = np.array([b["h"] for b in bars])
L = np.array([b["l"] for b in bars]); C = np.array([b["c"] for b in bars])
N = len(C); print(f"{N} M5 bars")


def ema(x, n):
    a = 2.0/(n+1); e = np.empty_like(x); e[0] = x[0]
    for i in range(1, len(x)): e[i] = x[i]*a + e[i-1]*(1-a)
    return e


def rsi(x, n=14):
    d = np.diff(x, prepend=x[0]); g = np.where(d > 0, d, 0.0); l = np.where(d < 0, -d, 0.0)
    ag = np.empty_like(x); al = np.empty_like(x); ag[0] = g[0]; al[0] = l[0]
    k = 1.0/n
    for i in range(1, len(x)):
        ag[i] = ag[i-1] + k*(g[i]-ag[i-1]); al[i] = al[i-1] + k*(l[i]-al[i-1])
    rs = np.where(al == 0, 100.0, ag/np.maximum(al, 1e-12))
    return 100 - 100/(1+rs)


def atr(h, l, c, n=14):
    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum(h-l, np.maximum(np.abs(h-pc), np.abs(l-pc)))
    a = np.empty_like(tr); a[0] = tr[0]; k = 1.0/n
    for i in range(1, len(tr)): a[i] = a[i-1] + k*(tr[i]-a[i-1])
    return a


print("precomputing indicators...")
A = atr(H, L, C)
RSI = rsi(C)
EMA = {n: ema(C, n) for n in (10, 20, 30, 50, 100, 200)}


def backtest(i0, i1, rr, atr_mult, rsi_lo, rsi_hi, fast, slow, cost=0.35, risk_pct=0.6, start_eq=10000.0):
    ef, es = EMA[fast], EMA[slow]
    eq = start_eq; peak = eq; maxdd = 0.0; trades = 0; wins = 0
    pos = None; day_start = eq; wk = -1; mon = -1; wk_start = eq; cur_wk = None; cur_mon = None
    blocked_d = blocked_w = False
    day = None
    day_pnl = 0.0
    for i in range(max(i0, slow+5), i1-1):
        d = T[i] // 86400; w = T[i] // (86400*7); m = T[i] // (86400*30)
        if d != day:
            day = d; day_start = eq; blocked_d = False
        if w != cur_wk:
            cur_wk = w; wk_start = eq; blocked_w = False
        if eq <= day_start*(1-0.03): blocked_d = True
        if eq <= wk_start*(1-0.05): blocked_w = True
        if pos is not None:
            hi, lo = H[i], L[i]
            sl = (pos[0] == 1 and lo <= pos[2]) or (pos[0] == -1 and hi >= pos[2])
            tp = (pos[0] == 1 and hi >= pos[3]) or (pos[0] == -1 and lo <= pos[3])
            ex = pos[2] if sl else (pos[3] if tp else None)
            if ex is not None:
                pnl = (ex - pos[1])*pos[0] - cost
                r_usd = pnl / max(pos[4], 1e-9) * pos[4]  # pnl in USD/oz * units
                # convert: risk_usd = eq*risk%; units = risk_usd/stopdist
                units = pos[5]
                pnl_usd = pnl * units
                eq += pnl_usd
                trades += 1
                if pnl_usd > 0: wins += 1
                peak = max(peak, eq); maxdd = max(maxdd, peak-eq)
                pos = None
                continue
        if pos is None and not blocked_d and not blocked_w:
            if ef[i] > es[i] and rsi_lo <= RSI[i] <= rsi_hi:
                side = 1
            elif ef[i] < es[i] and rsi_lo <= RSI[i] <= rsi_hi:
                side = -1
            else:
                side = 0
            if side:
                a = A[i]
                if a <= 0: continue
                sd = a*atr_mult; e = C[i]
                stp = e - sd*side; tgt = e + rr*sd*side
                risk_usd = eq*risk_pct/100
                units = risk_usd/sd
                pos = (side, e, stp, tgt, sd, units)
    return eq, trades, wins, maxdd


# split: year1 train [0 .. split], year2 test [split .. end]
split = int(N*0.5)
t0, t1 = T[0], T[split], T[-1]
print("train:", __import__('datetime').datetime.utcfromtimestamp(t0).date(), "->",
      __import__('datetime').datetime.utcfromtimestamp(t1).date(),
      "| test ->", __import__('datetime').datetime.utcfromtimestamp(T[-1]).date())

grid = list(itertools.product(
    (1.0, 1.5, 2.0, 3.0),        # rr
    (1.0, 1.5, 2.0, 2.5),        # atr_mult
    ((20, 70), (30, 65), (35, 60), (25, 75)),  # rsi band
    ((10, 50), (20, 100), (20, 50), (30, 100)),  # ema fast/slow
))
print(f"sweeping {len(grid)} configs on YEAR 1...")
results = []
for rr, am, (rl, rh), (f, s) in grid:
    eq, tr, wn, dd = backtest(0, split, rr, am, rl, rh, f, s)
    if tr >= 50:
        results.append((eq, tr, wn, dd, rr, am, rl, rh, f, s))
results.sort(reverse=True)
print("TOP 8 on year 1 (eq, trades, wins, maxdd, cfg):")
for r in results[:8]:
    print("  eq=%.0f tr=%d win=%.1f%% dd=%.0f rr=%.1f atr=%.1f rsi=%s ema=%s" %
          (r[0], r[1], 100*r[2]/r[1], r[3], r[4], r[5], (r[6], r[7]), (r[8], r[9])))
best = results[0] if results else None
if best:
    eq2, tr2, wn2, dd2 = backtest(split, N, best[4], best[5], best[6], best[7], best[8], best[9])
    print("\nWALK-FORWARD: best year-1 config on YEAR 2 (out-of-sample):")
    print("  eq=%.0f trades=%d win=%.1f%% maxdd=%.0f  return=%.1f%%" %
          (eq2, tr2, 100*wn2/max(tr2,1), dd2, (eq2-10000)/100))
    json.dump({"best_train": best[:10], "oos_eq": eq2, "oos_trades": tr2,
               "oos_win": wn2/max(tr2,1), "oos_dd": dd2, "oos_return_pct": (eq2-10000)/100},
              open("reports/xau_sweep.json", "w"), indent=2)
