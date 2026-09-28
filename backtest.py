"""Backtest the exact live strategy on historical candles (feed.py).
Same signal + same ATR stop / RR, walk-forward bar by bar.
Usage: python3 backtest.py [symbol] [interval] [range]
"""
import sys, json
from datetime import datetime, timezone
import feed, strategy, risk

def run(symbol, interval="1h", rng="1y", rr=1.5, warmup=210):
    cs = feed.candles(symbol, interval=interval, rng=rng)
    if len(cs) < warmup + 10:
        return {"symbol": symbol, "error": f"only {len(cs)} candles"}
    trades = []
    for i in range(warmup, len(cs)):
        window = cs[:i+1]
        sig = strategy.signal(window)
        if not sig:
            continue
        entry = sig["price"]; sl_d = sig["sl_dist"]
        if sl_d <= 0: continue
        if sig["side"] == "buy":
            sl, tp = entry - sl_d, entry + sl_d * rr
        else:
            sl, tp = entry + sl_d, entry - sl_d * rr
        # walk forward to see which hit first
        outcome = None
        for j in range(i+1, min(i+200, len(cs))):
            h, l = cs[j]["h"], cs[j]["l"]
            if sig["side"] == "buy":
                if l <= sl: outcome = ("SL", -1.0); break
                if h >= tp: outcome = ("TP", rr); break
            else:
                if h >= sl: outcome = ("SL", -1.0); break
                if l <= tp: outcome = ("TP", rr); break
        if outcome:
            trades.append((cs[i]["t"], sig["side"], outcome[0], outcome[1]))
    if not trades:
        return {"symbol": symbol, "trades": 0}
    wins = [t for t in trades if t[3] > 0]
    R = sum(t[3] for t in trades) / len(trades)
    eq = 1.0
    peak = 1.0; maxdd = 0.0
    for t in trades:
        eq *= (1 + 0.01 * t[3])   # 1% risk per trade
        peak = max(peak, eq); maxdd = min(maxdd, eq/peak - 1)
    return {"symbol": symbol, "interval": interval, "range": rng,
            "trades": len(trades), "win_rate": round(len(wins)/len(trades), 3),
            "avg_R": round(R, 3), "expectancy_R": round(R, 3),
            "return_pct_1risk": round((eq-1)*100, 2),
            "max_dd_pct": round(maxdd*100, 2)}

if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "EURUSD"
    itv = sys.argv[2] if len(sys.argv) > 2 else "1h"
    rng = sys.argv[3] if len(sys.argv) > 3 else "1y"
    print(json.dumps(run(sym, itv, rng), indent=2))
