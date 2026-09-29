#!/usr/bin/env python3
"""fetch_gold.py - fetch real XAUUSD/gold bars (2y) from free endpoints, cache them.

Tries, in order: Yahoo XAUUSD=X, Yahoo GC=F (COMEX futures), Yahoo XAU=X.
Keeps 1h (>= M5 as the bounty requires "M5 and up") for the longest window.
Writes xau/data/XAUUSD_1h.json (list of {t,o,h,l,c}) - real data only.
"""
import os, json, time, urllib.request, datetime as dt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}


def try_yahoo(sym, interval, rng):
    u = (f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
         f"?interval={interval}&range={rng}&includePrePost=false")
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25)
        j = json.loads(r.read())
        res = j["chart"]["result"][0]
        ts = res.get("timestamp") or []
        q = res["indicators"]["quote"][0]
        o, h, l, c = q.get("open"), q.get("high"), q.get("low"), q.get("close")
        bars = []
        for i in range(len(ts)):
            if None in (o[i], h[i], l[i], c[i]): continue
            bars.append({"t": ts[i], "o": o[i], "h": h[i], "l": l[i], "c": c[i]})
        return bars
    except Exception as e:
        print(f"  {sym} {interval} {rng}: ERR {str(e)[:80]}")
        return []


def main():
    best = []
    for sym in ("XAUUSD=X", "GC=F", "XAU=X"):
        for interval, rng in (("1h", "730d"), ("1h", "365d"), ("1d", "730d")):
            print(f"trying {sym} {interval} {rng} ...")
            b = try_yahoo(sym, interval, rng)
            if len(b) > len(best):
                best = b
                print(f"  -> {len(b)} bars from {sym} {interval} {rng}")
                json.dump(b, open(os.path.join(OUT, "XAUUSD_1h.json"), "w"))
            if len(b) >= 3000:
                break
            time.sleep(1)
    if best:
        t0 = dt.datetime.utcfromtimestamp(best[0]["t"]).strftime("%Y-%m-%d")
        t1 = dt.datetime.utcfromtimestamp(best[-1]["t"]).strftime("%Y-%m-%d")
        print(f"CACHED {len(best)} bars  {t0} -> {t1}")
    else:
        print("NO DATA FETCHED")


if __name__ == "__main__":
    main()
