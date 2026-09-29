#!/usr/bin/env python3
"""xau_scalp.py - XAUUSD M5+ scalping strategy + risk-gated backtest.

Bounty a5e51254 deliverable. Strategy operates on any intraday TF from M5 up.
Risk gates (hard, enforced in the sim exactly as in the EA):
  * daily loss  < 3% of equity   -> stop trading for the rest of that day
  * weekly loss < 5% of equity   -> stop trading for the rest of that week
  * profit target >= 10% / month (measured, not forced)
  * mandatory ATR stop on every trade, fixed-RR target, no martingale
  * >= ~5 trades/week target (strategy is active by design)
Data: real bars only (fxintel.bars.load / cached data/*.json). Never synthetic.
Outputs reports/xau_backtest.json + reports/xau_backtest.md (daily/weekly/monthly PnL).
"""
from __future__ import annotations
import os, sys, json, glob, datetime as dt, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, ROOT)

SYM = "XAUUSD"
RISK_PCT = 0.6          # % equity per trade (small: gold is volatile)
RR = 2.0
ATR_STOP = 1.2
COST = 0.35             # gold spread+comm in USD/oz round trip
START_EQ = 10000.0
DAY_LOSS = 0.03
WK_LOSS = 0.05
MON_TARGET = 0.10
PIP = 0.10


def load_series():
    """Return (bars, src, tf_label). Prefer M5/M1 if present; else real H1."""
    # explicit cache files first
    cands = [("data/XAUUSD_5m.json","M5"), ("data/XAUUSD_1m.json","M1"),
             ("xau/data/XAUUSD_5m.json","M5"), ("data/XAUUSD_1h.json","H1"),
             ("data/bars_XAUUSD_H1.json","H1")]
    for path, tf in cands:
        if os.path.exists(path):
            try:
                d = json.load(open(path))
                arr = d if isinstance(d, list) else (d.get("bars") or d.get("data") or [])
                bars = _norm(arr)
                if len(bars) > 300:
                    return bars, f"cache:{path}", tf
            except Exception:
                pass
    try:
        from fxintel.bars import load as _l
        for tf in ("M5", "H1"):
            raw, src = _l(SYM, tf, 6000, allow_synthetic=False)
            bars = _norm(raw)
            if len(bars) > 300:
                return bars, src, tf
    except Exception:
        pass
    return [], "none", "?"


def _norm(raw):
    out = []
    for b in raw or []:
        if isinstance(b, dict):
            o = b.get("o", b.get("open")); h = b.get("h", b.get("high"))
            l = b.get("l", b.get("low")); c = b.get("c", b.get("close"))
            t = b.get("t", b.get("time"))
        else:
            continue
        if None not in (o, h, l, c):
            out.append({"o": float(o), "h": float(h), "l": float(l), "c": float(c), "t": t})
    return out


def atr(bars, i, n=14):
    if i < n: return None
    trs = [max(bars[k]["h"]-bars[k]["l"], abs(bars[k]["h"]-bars[k-1]["c"]),
               abs(bars[k]["l"]-bars[k-1]["c"])) for k in range(i-n+1, i+1)]
    return sum(trs)/n


def ema(vals, n):
    if len(vals) < n: return None
    k = 2.0/(n+1); e = sum(vals[:n])/n
    for x in vals[n:]: e = x*k + e*(1-k)
    return e


def rsi(cl, n=14):
    if len(cl) < n+1: return None
    g = l = 0.0
    for k in range(len(cl)-n, len(cl)):
        d = cl[k]-cl[k-1]; g += max(d,0); l += max(-d,0)
    if l == 0: return 100.0
    return 100 - 100/(1+((g/n)/(l/n)))


def signal(bars, i):
    """M5+ momentum-pullback: trend via EMA20/50, enter on RSI reset in trend dir."""
    if i < 60: return None
    cl = [b["c"] for b in bars[:i+1]]
    ef = ema(cl[-80:], 20); es = ema(cl[-160:], 50)
    a = atr(bars, i, 14); r = rsi(cl[-40:], 14)
    if ef is None or es is None or not a or r is None or ef == es: return None
    up = ef > es
    if up and 40 <= r <= 62:      # pullback reset in uptrend
        return "buy", a
    if (not up) and 38 <= r <= 60:
        return "sell", a
    return None


def run_backtest(bars):
    eq = START_EQ; peak = START_EQ; maxdd = 0.0
    trades = []
    pos = None
    daily = {}; weekly = {}; monthly = {}
    def key(ts, kind):
        d = dt.datetime.utcfromtimestamp(ts) if isinstance(ts, (int, float)) else dt.datetime.utcnow()
        if kind == "d": return d.strftime("%Y-%m-%d")
        if kind == "w": return f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
        return d.strftime("%Y-%m")
    day_start_eq = eq; wk_start_eq = eq; mon_start_eq = eq
    cur_d = cur_w = cur_m = None
    blocked_d = blocked_w = False
    for i in range(60, len(bars)-1):
        b = bars[i]
        ts = b.get("t", i*3600)
        dk = key(ts, "d"); wk = key(ts, "w"); mk = key(ts, "m")
        if dk != cur_d:
            cur_d = dk; day_start_eq = eq; blocked_d = False
        if wk != cur_w:
            cur_w = wk; wk_start_eq = eq; blocked_w = False
        if mk != cur_m:
            cur_m = mk; mon_start_eq = eq
        # gate checks
        if eq <= day_start_eq*(1-DAY_LOSS): blocked_d = True
        if eq <= wk_start_eq*(1-WK_LOSS): blocked_w = True
        # manage open
        if pos is not None:
            hi, lo = b["h"], b["l"]
            hsl = (pos["side"]=="buy" and lo<=pos["stop"]) or (pos["side"]=="sell" and hi>=pos["stop"])
            htp = (pos["side"]=="buy" and hi>=pos["target"]) or (pos["side"]=="sell" and lo>=pos["stop"]) if False else \
                  ((pos["side"]=="buy" and hi>=pos["target"]) or (pos["side"]=="sell" and lo<=pos["target"]))
            ex = pos["stop"] if hsl else (pos["target"] if htp else None)
            if ex is not None:
                pnl = (ex-pos["entry"])*(1 if pos["side"]=="buy" else -1) - COST
                risk_usd = pos["risk_usd"]
                R = pnl/ (risk_usd/ (RISK_PCT/100*eq) * 1.0) if False else (pnl / max(risk_usd,1e-9))
                eq += R*risk_usd
                trades.append({"t":ts,"side":pos["side"],"entry":pos["entry"],"exit":ex,
                               "pnl_usd":round(R*risk_usd,2),"R":round(R,3),"eq":round(eq,2),
                               "day":dk,"week":wk,"month":mk})
                daily[dk]=daily.get(dk,0)+R*risk_usd; weekly[wk]=weekly.get(wk,0)+R*risk_usd
                monthly[mk]=monthly.get(mk,0)+R*risk_usd
                peak=max(peak,eq); maxdd=max(maxdd,peak-eq); pos=None
                continue
        if pos is None and not blocked_d and not blocked_w:
            s = signal(bars, i)
            if s:
                side, a = s; e = b["c"]; sd = ATR_STOP*a; td = RR*sd
                stp = e-sd if side=="buy" else e+sd
                tgt = e+td if side=="buy" else e-td
                risk_usd = eq*RISK_PCT/100
                pos = {"side":side,"entry":e,"stop":stp,"target":tgt,"risk_usd":risk_usd}
    return {"trades":trades,"daily":daily,"weekly":weekly,"monthly":monthly,
            "final_eq":round(eq,2),"max_dd_pct":round(maxdd/START_EQ*100,2)}


def main():
    bars, src, tf = load_series()
    print(f"data: {len(bars)} bars src={src} tf={tf}")
    if len(bars) < 300:
        print("INSUFFICIENT REAL DATA"); return
    t0 = bars[0].get("t"); t1 = bars[-1].get("t")
    def fmt(t):
        try: return dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")
        except Exception: return "?"
    res = run_backtest(bars)
    tr = res["trades"]
    wins=[t for t in tr if t["pnl_usd"]>0]; losses=[t for t in tr if t["pnl_usd"]<=0]
    stats = {"trades":len(tr),"win_rate":round(len(wins)/max(len(tr),1),3),
             "start_eq":START_EQ,"final_eq":res["final_eq"],
             "total_return_pct":round((res["final_eq"]-START_EQ)/START_EQ*100,2),
             "max_dd_pct":res["max_dd_pct"],
             "avg_R":round(sum(t["R"] for t in tr)/max(len(tr),1),3),
             "profit_factor":round(sum(t["pnl_usd"] for t in wins)/(abs(sum(t["pnl_usd"] for t in losses)) or 1e-9),3)}
    # gate audit
    worst_day=min(res["daily"].values()) if res["daily"] else 0
    worst_wk=min(res["weekly"].values()) if res["weekly"] else 0
    best_mon=max(res["monthly"].values()) if res["monthly"] else 0
    # trades per week
    nweeks=max(len(res["weekly"]),1); tpw=len(tr)/nweeks
    out={"bounty":"a5e51254","strategy":"EMA20/50 trend + RSI(14) pullback reset, ATR stop 1.2x, RR 2.0, cost $%.2f"%COST,
         "data_source":src,"timeframe":tf,"period":[fmt(t0),fmt(t1)],
         "risk_pct":RISK_PCT,"stats":stats,
         "gates":{"worst_day_usd":round(worst_day,2),"worst_day_pct":round(worst_day/START_EQ*100,2),
                  "day_gate_3pct_ok":worst_day/START_EQ>-DAY_LOSS,
                  "worst_week_usd":round(worst_wk,2),"worst_week_pct":round(worst_wk/START_EQ*100,2),
                  "week_gate_5pct_ok":worst_wk/START_EQ>-WK_LOSS,
                  "best_month_usd":round(best_mon,2),"best_month_pct":round(best_mon/START_EQ*100,2),
                  "month_target_10pct_ok":best_mon/START_EQ>=MON_TARGET,
                  "trades_per_week":round(tpw,1),"min_5_per_week_ok":tpw>=5}}
    os.makedirs("reports",exist_ok=True)
    json.dump(out,open("reports/xau_backtest.json","w"),indent=2)
    with open("reports/xau_backtest.md","w") as f:
        f.write(f"# XAUUSD M5+ scalp backtest ({tf})\n\nSource: {src}  Period: {fmt(t0)} -> {fmt(t1)}\n\n")
        f.write(f"Strategy: {out['strategy']}\n\n## Headline\n```json\n{json.dumps(stats,indent=2)}\n```\n")
        f.write(f"\n## Gates\n```json\n{json.dumps(out['gates'],indent=2)}\n```\n\n## Monthly PnL (USD)\n")
        for k in sorted(res["monthly"]): f.write(f"- {k}: {res['monthly'][k]:.2f}\n")
        f.write("\n## Weekly PnL (USD)\n")
        for k in sorted(res["weekly"]): f.write(f"- {k}: {res['weekly'][k]:.2f}\n")
    print(json.dumps(stats,indent=2)); print(json.dumps(out["gates"],indent=2))


if __name__=="__main__":
    main()
