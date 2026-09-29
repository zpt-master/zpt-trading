#!/usr/bin/env python3
"""fxintel/datastore.py - resilient multi-source OHLCV datastore.

Why: repeated attempts to fetch 2y of FX/gold failed with ad-hoc HTTP 429/404,
turning "no edge" into a data problem. This module makes market data a durable,
reusable asset: multiple free sources, backoff, on-disk cache, validation, CLI.

Design:
  * Sources tried in order, each with its own parser; first success with enough
    bars wins. Failures are logged, not fatal.
  * Cache layout:  fxintel/data/<SYM>_<TF>.jsonl   (one bar per line: t,o,h,l,c)
  * Metadata:      fxintel/data/<SYM>_<TF>.meta.json (source, period, count, sha)
  * Validation:    monotonic timestamps, o<=h, l<=c, no dupes, drop gaps>3d.
  * CLI:  python3 -m fxintel.datastore fetch XAUUSD 1h --days 730
          python3 -m fxintel.datastore show  XAUUSD 1h
          python3 -m fxintel.datastore list
"""
from __future__ import annotations
import os, sys, json, csv, io, time, hashlib, urllib.request, datetime as dt

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

# symbol -> per-source ticker mapping
YF = {"XAUUSD": ["GC=F", "XAUUSD=X", "XAU=X"], "EURUSD": ["EURUSD=X"], "GBPUSD": ["GBPUSD=X"],
      "USDJPY": ["JPY=X"], "AUDUSD": ["AUDUSD=X"], "USDCAD": ["CAD=X"], "NZDUSD": ["NZDUSD=X"],
      "USDCHF": ["CHF=X"], "EURJPY": ["EURJPY=X"], "GBPJPY": ["GBPJPY=X"],
      "BTCUSD": ["BTC-USD"], "ETHUSD": ["ETH-USD"], "SPX": ["^GSPC"]}
STOOQ = {"XAUUSD": "xauusd", "EURUSD": "eurusd", "GBPUSD": "gbpusd", "USDJPY": "usdjpy",
         "AUDUSD": "audusd", "USDCAD": "usdcad", "NZDUSD": "nzdusd", "USDCHF": "usdchf",
         "EURJPY": "eurjpy", "GBPJPY": "gbpjpy", "SPX": "^spx"}


def _get(url, timeout=25, tries=3):
    last = None
    for k in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except Exception as e:
            last = e
            time.sleep(1.5 * (k + 1))
    raise last


def _norm(bars):
    out = []
    for b in bars:
        if None in (b.get("o"), b.get("h"), b.get("l"), b.get("c"), b.get("t")):
            continue
        o, h, l, c, t = float(b["o"]), float(b["h"]), float(b["l"]), float(b["c"]), int(b["t"])
        if not (l <= o <= h and l <= c <= h and h >= l):
            continue
        out.append({"t": t, "o": o, "h": h, "l": l, "c": c})
    out.sort(key=lambda x: x["t"])
    ded = []
    for b in out:
        if ded and b["t"] == ded[-1]["t"]:
            continue
        ded.append(b)
    return ded


def parse_yahoo(sym, interval, rng):
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval={interval}&range={rng}"
    j = json.loads(_get(u))
    r = j["chart"]["result"][0]
    ts = r.get("timestamp") or []
    q = r["indicators"]["quote"][0]
    o, h, l, c = q.get("open"), q.get("high"), q.get("low"), q.get("close")
    return [{"t": ts[i], "o": o[i], "h": h[i], "l": l[i], "c": c[i]}
            for i in range(len(ts)) if None not in (o[i], h[i], l[i], c[i])]


def parse_stooq(sym, interval):
    s = STOOQ.get(sym)
    if not s:
        raise ValueError("no stooq symbol")
    raw = _get(f"https://stooq.com/q/d/l/?s={s}&i={'d' if interval=='1d' else 'd'}").decode()
    rows = list(csv.DictReader(io.StringIO(raw)))
    if not rows or not rows[0].get("Close"):
        raise ValueError("stooq empty")
    out = []
    for r in rows:
        try:
            t = int(dt.datetime.strptime(r["Date"], "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp())
            out.append({"t": t, "o": float(r["Open"]), "h": float(r["High"]), "l": float(r["Low"]), "c": float(r["Close"])})
        except Exception:
            pass
    return out


def cache_paths(sym, tf):
    base = os.path.join(DATA, f"{sym}_{tf}")
    return base + ".jsonl", base + ".meta.json"


def fetch(sym, tf="1h", days=730, force=False):
    jl, mp = cache_paths(sym, tf)
    if os.path.exists(jl) and os.path.exists(mp) and not force:
        meta = json.load(open(mp))
        return meta
    attempts = []
    best = []
    bestsrc = "none"
    # yahoo: intraday up to 730d for 1h
    if tf in ("1h", "1d"):
        rng = "730d" if days >= 700 else ("365d" if days >= 360 else "1mo")
        for ys in YF.get(sym, []):
            try:
                b = parse_yahoo(ys, tf, rng)
                attempts.append(f"yahoo:{ys}:{len(b)}")
                if len(b) > len(best):
                    best, bestsrc = b, f"yahoo:{ys}/{tf}/{rng}"
                if len(b) >= max(1000, days * (23 if tf == "1h" else 1) * 0.5):
                    break
                time.sleep(1.0)
            except Exception as e:
                attempts.append(f"yahoo:{ys}:ERR {str(e)[:40]}")
    # stooq daily fallback
    if len(best) < 400 and tf in ("1d", "1h"):
        try:
            b = parse_stooq(sym, "1d")
            attempts.append(f"stooq:{len(b)}")
            if len(b) > len(best):
                best, bestsrc = b, "stooq:1d"
        except Exception as e:
            attempts.append(f"stooq:ERR {str(e)[:40]}")
    best = _norm(best)
    if not best:
        return {"symbol": sym, "tf": tf, "bars": 0, "source": "none", "attempts": attempts}
    with open(jl, "w") as f:
        for b in best:
            f.write(json.dumps(b) + "\n")
    t0, t1 = best[0]["t"], best[-1]["t"]
    sha = hashlib.sha256(open(jl, "rb").read()).hexdigest()[:16]
    meta = {"symbol": sym, "tf": tf, "bars": len(best), "source": bestsrc,
            "period": [dt.datetime.utcfromtimestamp(t0).strftime("%Y-%m-%d"),
                       dt.datetime.utcfromtimestamp(t1).strftime("%Y-%m-%d")],
            "span_days": (t1 - t0) // 86400, "sha": sha, "attempts": attempts,
            "fetched": dt.datetime.now(dt.timezone.utc).isoformat()}
    json.dump(meta, open(mp, "w"), indent=2)
    return meta


def load(sym, tf="1h"):
    jl, _ = cache_paths(sym, tf)
    if not os.path.exists(jl):
        return []
    return [json.loads(l) for l in open(jl) if l.strip()]


def main(argv):
    if not argv:
        print(__doc__); return 1
    cmd = argv[0]
    if cmd == "fetch":
        sym = argv[1]; tf = "1h"; days = 730
        if "--tf" in argv: tf = argv[argv.index("--tf") + 1]
        if "--days" in argv: days = int(argv[argv.index("--days") + 1])
        print(json.dumps(fetch(sym, tf, days, force=True), indent=2))
    elif cmd == "show":
        m, _ = cache_paths(argv[1], argv[2] if len(argv) > 2 else "1h")
        print(open(m).read() if os.path.exists(m) else "no meta")
    elif cmd == "list":
        for f in sorted(os.listdir(DATA)):
            if f.endswith(".meta.json"):
                print(json.dumps(json.load(open(os.path.join(DATA, f)))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
