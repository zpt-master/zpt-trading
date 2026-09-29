#!/usr/bin/env python3
"""xau/sweep_pure.py - param sweep + walk-forward, PURE Python (no numpy).

Same rule set as the EA. Precompute indicators once, then evaluate a config grid
on year 1 and test the best on year 2 (out-of-sample, no lookahead).
"""
import json, time, datetime as dt

bars = json.load(open("data/XAUUSD_5m.json"))
n = len(bars)
T = [b["t"] for b in bars]; O = [b["o"] for b in bars]
H = [b["h"] for b in bars]; L = [b["l"] for b in bars]; C = [b["c"] for b in bars]
print(f"{n} M5 bars  {dt.datetime.utcfromtimestamp(T[0]).date()} -> {dt.datetime.utcfromtimestamp(T[-1]).date()}")


def ema(x, p):
    a = 2.0/(p+1); e = [0.0]*len(x); e[0] = x[0]
    for i in range(1, len(x)): e[i] = x[i]*a + e[i-1]*(1-a)
    return e


def rsi(x, p=14):
    g = [0.0]*len(x); l = [0.0]*len(x); k = 1.0/p
    for i in range(1, len(x)):
        d = x[i]-x[i-1]
        g[i] = max(d, 0.0); l[i] = max(-d, 0.0)
    ag = [0.0]*len(x); al = [0.0]*len(x); ag[0] = g[0]; al[0] = l[0]
    for i in range(1, len(x)):
        ag[i] = ag[i-1] + k*(g[i]-ag[i-1]); al[i] = al[i-1] + k*(l[i]-al[i-1])
    out = [0.0]*len(x)
    for i in range(len(x)):
        out[i] = 100.0 if al[i] <= 1e-12 else 100 - 100/(1 + ag[i]/al[i])
    return out


def atr(h, l, c, p=14):
    k = 1.0/p; a = [0.0]*len(c)
    a[0] = h[0]-l[0]
    for i in range(1, len(c)):
        tr = max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1]))
        a[i] = a[i-1] + k*(tr-a[i-1])
    return a


print("precomputing indicators...", flush=True); t0 = time.time()
A = atr(H, L, C); R = rsi(C)
E = {p: ema(C, p) for p in (10, 20, 30, 50, 100, 200)}
print(f"  done in {time.time()-t0:.1f}s", flush=True)


def bt(i0, i1, rr, am, rl, rh, f, s, cost=0.35, risk_pct=0.6, eq0=10000.0):
    ef = E[f]; es = E[s]
    eq = eq0; peak = eq; mdd = 0.0; tr = 0; wn = 0
    inpos = False; side = 0; ent = 0.0; stp = 0.0; tgt = 0.0; units = 0.0
    day = -1; dstart = eq; wk = -1; wstart = eq; bd = False; bw = False
    for i in range(max(i0, s+5), i1-1):
        t = T[i]; d = t // 86400; w = t // 604800
        if d != day: day = d; dstart = eq; bd = False
        if w != wk: wk = w; wstart = eq; bw = False
        if eq <= dstart*0.97: bd = True
        if eq <= wstart*0.95: bw = True
        if inpos:
            hi = H[i]; lo = L[i]
            hit = 0
            if side == 1:
                if lo <= stp: hit = -1
                elif hi >= tgt: hit = 1
            else:
                if hi >= stp: hit = -1
                elif lo <= tgt: hit = 1
            if hit:
                ex = stp if hit < 0 else tgt
                pnl = (ex-ent)*side - cost
                eq += pnl*units
                tr += 1
                if pnl > 0: wn += 1
                if eq > peak: peak = eq
                dd = peak-eq
                if dd > mdd: mdd = dd
                inpos = False
            continue
        if not bd and not bw:
            rs = R[i]; up = ef[i] > es[i]
            sd = 0
            if up and rl <= rs <= rh: sd = 1
            elif (not up) and rl <= rs <= rh: sd = -1
            if sd:
                a = A[i]
                if a > 0:
                    st = a*am; e = C[i]
                    side = sd; ent = e; stp = e-st*sd; tgt = e+rr*st*sd
                    units = (eq*risk_pct/100.0)/st
                    inpos = True
    return eq, tr, wn, mdd


split = n//2
print("train:", dt.datetime.utcfromtimestamp(T[0]).date(), "->", dt.datetime.utcfromtimestamp(T[split]).date(),
      "| test ->", dt.datetime.utcfromtimestamp(T[-1]).date())
grid = []
for rr in (1.0, 1.5, 2.0, 3.0):
    for am in (1.0, 1.5, 2.0):
        for band in ((20, 70), (30, 65), (35, 60)):
            for fs in ((10, 50), (20, 100), (20, 50), (30, 100)):
                grid.append((rr, am, band[0], band[1], fs[0], fs[1]))
print(f"sweeping {len(grid)} configs on YEAR 1...", flush=True)
res = []; t0 = time.time()
for c in grid:
    eq, tr, wn, dd = bt(0, split, *c)
    if tr >= 50:
        res.append((eq, tr, wn, dd) + c)
res.sort(reverse=True)
print(f"  swept in {time.time()-t0:.1f}s; {len(res)} configs with >=50 trades")
for r in res[:8]:
    print("  eq=%7.0f tr=%5d win=%4.1f%% dd=%6.0f rr=%.1f atr=%.1f rsi=(%d,%d) ema=(%d,%d)" %
          (r[0], r[1], 100*r[2]/r[1], r[3], r[4], r[5], r[6], r[7], r[8], r[9]))
out = {"grid": len(grid), "evaluated": len(res)}
if res:
    b = res[0]
    eq2, tr2, wn2, dd2 = bt(split, n, b[4], b[5], b[6], b[7], b[8], b[9])
    print("\nWALK-FORWARD best(trained on Y1) -> YEAR 2 OUT-OF-SAMPLE:")
    print("  eq=%.0f trades=%d win=%.1f%% maxdd=%.0f return=%.1f%%" %
          (eq2, tr2, 100*wn2/max(tr2, 1), dd2, (eq2-10000)/100.0))
    out.update({"best": list(b), "oos_eq": eq2, "oos_tr": tr2, "oos_win": wn2/max(tr2, 1),
                "oos_dd": dd2, "oos_return_pct": (eq2-10000)/100.0})
json.dump(out, open("reports/xau_sweep.json", "w"), indent=2)
print("wrote reports/xau_sweep.json")
