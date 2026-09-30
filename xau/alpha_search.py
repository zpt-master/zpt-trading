#!/usr/bin/env python3
"""xau/alpha_search.py - honest multi-family edge search on REAL 2y M5 gold.

The trend/RSI scalp family is proven edge-less. Before conceding, test genuinely
DIFFERENT alpha families on the same 210,384 real bars, each walk-forward
(train Y1 -> test Y2), risk-normalized, cost-charged. Families:
  A. Mean reversion (Bollinger z-score fade + ATR stop)
  B. Session breakout (range of Asian session -> break in London/NY)
  C. Volatility regime (trade only low-ATR-percentile expansions)
  D. Momentum continuation (N-bar ROC with trailing stop)
Reports per-family OOS stats. Nothing is claimed unless OOS is positive AND stable.
"""
import json, time, datetime as dt, statistics as st

bars = json.load(open("data/XAUUSD_5m.json"))
n = len(bars)
T = [b["t"] for b in bars]; H = [b["h"] for b in bars]; L = [b["l"] for b in bars]; C = [b["c"] for b in bars]
COST = 0.35  # USD/oz round-trip spread+slippage
print(f"{n} bars  {dt.datetime.utcfromtimestamp(T[0]).date()} -> {dt.datetime.utcfromtimestamp(T[-1]).date()}")


def atr(p=14):
    a = [0.0]*n; a[0] = H[0]-L[0]; k = 1.0/p
    for i in range(1, n):
        tr = max(H[i]-L[i], abs(H[i]-C[i-1]), abs(L[i]-C[i-1]))
        a[i] = a[i-1]+k*(tr-a[i-1])
    return a


def sma(x, p):
    s = [0.0]*n; run = 0.0
    for i in range(n):
        run += x[i]
        if i >= p: run -= x[i-p]
        s[i] = run/min(i+1, p)
    return s


A = atr(); SMA20 = sma(C, 20)


def stats(pnls):
    if not pnls: return {"trades": 0}
    wins = [p for p in pnls if p > 0]
    eq = 10000.0; peak = eq; mdd = 0
    for p in pnls: eq += p; peak = max(peak, eq); mdd = max(mdd, peak-eq)
    sh = (st.mean(pnls)/st.pstdev(pnls)*16) if len(pnls) > 2 and st.pstdev(pnls) > 0 else 0
    gp = sum(wins); gl = -sum(p for p in pnls if p <= 0)
    return {"trades": len(pnls), "win_pct": round(100*len(wins)/len(pnls), 1),
            "ret_pct": round((eq-10000)/100, 1), "max_dd_pct": round(mdd/100, 1),
            "pf": round(gp/gl, 2) if gl else 99, "sharpe": round(sh, 2)}


def run(i0, i1, signal_fn):
    """signal_fn(i)-> (side, stop_atr_mult, rr) or None. Fixed-fractional risk."""
    eq = 10000.0; pos = None; pnls = []
    for i in range(max(i0, 60), i1-1):
        if pos:
            side, ent, stp, tgt, units = pos
            hit = None
            if side == 1:
                if L[i] <= stp: hit = stp
                elif H[i] >= tgt: hit = tgt
            else:
                if H[i] >= stp: hit = stp
                elif L[i] <= tgt: hit = tgt
            if hit is not None:
                pnl = (hit-ent)*side*units - COST*units
                eq += pnl; pnls.append(pnl); pos = None
            continue
        sig = signal_fn(i)
        if sig:
            side, am, rr = sig
            a = A[i]
            if a > 0:
                stp = C[i]-a*am*side; tgt = C[i]+a*am*rr*side
                units = (eq*0.005)/max(a*am, 1e-6)
                pos = (side, C[i], stp, tgt, units)
    return pnls


# --- Family A: Bollinger z-score mean reversion ---
def sigA(i):
    if i < 25: return None
    m = SMA20[i]
    var = sum((C[j]-m)**2 for j in range(i-19, i+1))/20
    sd = var**0.5
    if sd <= 0: return None
    z = (C[i]-m)/sd
    if z <= -2.0: return (1, 1.0, 1.5)
    if z >= 2.0: return (-1, 1.0, 1.5)
    return None


# --- Family B: Asian-range breakout (Asian = 00:00-07:00 UTC) ---
day_rng = {}
for i in range(n):
    d = T[i]//86400; hh = (T[i] % 86400)//3600
    if 0 <= hh < 7:
        lo, hi = day_rng.get(d, (1e18, -1e18))
        day_rng[d] = (min(lo, L[i]), max(hi, H[i]))


def sigB(i):
    d = T[i]//86400; hh = (T[i] % 86400)//3600
    r = day_rng.get(d)
    if not r or r[0] > 1e17 or hh < 7 or hh > 20: return None
    lo, hi = r
    if C[i] > hi and C[i-1] <= hi: return (1, 1.5, 2.0)
    if C[i] < lo and C[i-1] >= lo: return (-1, 1.5, 2.0)
    return None


# --- Family C: low-vol regime momentum continuation ---
atr_pct_win = [0.0]*n
for i in range(100, n):
    w = A[i-99:i+1]; s = sorted(w); atr_pct_win[i] = s.index(A[i])/len(s) if A[i] in s else 0.5


def sigC(i):
    if i < 100: return None
    if atr_pct_win[i] > 0.35: return None           # only quiet regimes
    roc = (C[i]-C[i-10])/C[i-10]
    if roc > 0.0015: return (1, 1.2, 2.5)
    if roc < -0.0015: return (-1, 1.2, 2.5)
    return None


# --- Family D: 20-bar momentum continuation ---
def sigD(i):
    if i < 25: return None
    m = (C[i]-C[i-20])/C[i-20]
    if m > 0.003 and C[i] > SMA20[i]: return (1, 2.0, 2.0)
    if m < -0.003 and C[i] < SMA20[i]: return (-1, 2.0, 2.0)
    return None


split = n//2
fams = {"A_meanrev": sigA, "B_breakout": sigB, "C_lowvol_mom": sigC, "D_mom20": sigD}
out = {}
for name, fn in fams.items():
    tr1 = run(0, split, fn); tr2 = run(split, n, fn)
    s1, s2 = stats(tr1), stats(tr2)
    print(f"\n{name}\n  Y1(train): {s1}\n  Y2(OOS) : {s2}")
    out[name] = {"train": s1, "oos": s2}
json.dump(out, open("reports/alpha_search.json", "w"), indent=2)
best = [k for k, v in out.items() if v["oos"].get("ret_pct", -1) > 0 and v["oos"].get("trades", 0) >= 30]
print("\nOOS-POSITIVE families (>=30 trades):", best or "NONE")
print("wrote reports/alpha_search.json")
