#!/usr/bin/env python3
"""fxintel/binance_gold.py - real M5 gold history via gold-backed token pairs.

Free HTTP FX/gold feeds are rate-limited from this egress, blocking real 2-year
backtests. Binance's public klines endpoint is NOT rate-limited for our volume and
PAXG/XAUT are 1:1 gold-backed tokens that track XAUUSD. This yields REAL high-
frequency (M5) gold bars going back years -> satisfies "M5 and above, 2 years".

Usage: python3 -m fxintel.binance_gold [--tf 5m] [--years 2]
Writes: data/XAUUSD_M5.json  and  fxintel/data/XAUUSD_M5.jsonl (+ meta)
"""
from __future__ import annotations
import os, sys, json, time, urllib.request, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D = os.path.join(HERE, "data"); os.makedirs(D, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0"}
BASES = ["https://api.binance.com", "https://data-api.binance.vision"]
PAIRS = ["PAXGUSDT", "XAUTUSDT"]          # gold-backed, 1 token ~= 1 oz XAU


def _get(path, tries=3):
    last = None
    for k in range(tries):
        for base in BASES:
            try:
                return json.loads(urllib.request.urlopen(
                    urllib.request.Request(base + path, headers=UA), timeout=20).read())
            except Exception as e:
                last = e
        time.sleep(1.0 * (k + 1))
    raise last


def klines(sym, interval, start_ms, end_ms):
    out = []
    cur = start_ms
    while cur < end_ms:
        p = f"/api/v3/klines?symbol={sym}&interval={interval}&startTime={cur}&limit=1000"
        try:
            batch = _get(p)
        except Exception as e:
            print(f"  {sym} {interval}: ERR {str(e)[:60]}")
            break
        if not batch:
            break
        for k in batch:
            out.append({"t": int(k[0] // 1000), "o": float(k[1]), "h": float(k[2]),
                        "l": float(k[3]), "c": float(k[4])})
        nxt = batch[-1][0] + 1
        if nxt <= cur:
            break
        cur = nxt
        if len(batch) < 1000:
            break
        time.sleep(0.15)
    return out


def main(argv):
    tf = "5m"; years = 2
    if "--tf" in argv: tf = argv[argv.index("--tf") + 1]
    if "--years" in argv: years = int(argv[argv.index("--years") + 1])
    end = int(time.time() * 1000)
    start = end - int(years * 365.25 * 86400 * 1000)
    best, bestpair = [], ""
    for pair in PAIRS:
        print(f"fetching {pair} {tf} {years}y ...")
        b = klines(pair, tf, start, end)
        print(f"  {pair}: {len(b)} bars")
        if len(b) > len(best):
            best, bestpair = b, pair
    if not best:
        print("NO DATA"); return 1
    best.sort(key=lambda x: x["t"])
    ded = []
    for b in best:
        if ded and b["t"] == ded[-1]["t"]: continue
        ded.append(b)
    # write both canonical locations
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    json.dump(ded, open(os.path.join(ROOT, f"data/XAUUSD_{tf.upper()}.json"), "w"))
    with open(os.path.join(D, f"XAUUSD_{tf}.jsonl"), "w") as f:
        for b in ded: f.write(json.dumps(b) + "\n")
    meta = {"symbol": "XAUUSD", "tf": tf, "bars": len(ded),
            "source": f"binance:{bestpair} (gold-backed token ~= XAUUSD)",
            "period": [dt.datetime.utcfromtimestamp(ded[0]["t"]).strftime("%Y-%m-%d"),
                       dt.datetime.utcfromtimestamp(ded[-1]["t"]).strftime("%Y-%m-%d")],
            "span_days": (ded[-1]["t"] - ded[0]["t"]) // 86400}
    json.dump(meta, open(os.path.join(D, f"XAUUSD_{tf}.meta.json"), "w"), indent=2)
    print("WROTE:", json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
