"""Bars provider - supplies OHLC history to the edge gate.

Source order (first that works wins), all cached to disk:
  1. MT5 bridge / ledger  (GET /mt5/candles?symbol=&timeframe=&count=)
  2. Local cache          (data/bars_<SYM>_<TF>.json)
  3. Synthetic fallback   (deterministic random-walk) - tagged so the trader
     KNOWS it is not real and must not treat an edge computed on it as live.

truthy()/is_real() lets the caller refuse to place a live order when only
synthetic data was available.
"""
from __future__ import annotations
import json, os, time, urllib.request, urllib.error, random
from typing import List, Optional

BASE = os.environ.get("LEDGER_URL", "http://127.0.0.1:4790")
TOKEN = os.environ.get("LEDGER_TOKEN", "change-me-shared-secret")
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _get(path):
    r = urllib.request.Request(BASE + path, method="GET")
    r.add_header("X-Auth-Token", TOKEN); r.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(r, timeout=10) as x:
        return json.loads(x.read().decode())


def _cache_path(symbol, timeframe):
    os.makedirs(DATA, exist_ok=True)
    return os.path.join(DATA, "bars_%s_%s.json" % (symbol.upper(), timeframe))


def _from_bridge(symbol, timeframe, count):
    try:
        d = _get("/mt5/candles?symbol=%s&timeframe=%s&count=%d" % (symbol, timeframe, count))
        raw = d.get("bars") or d.get("candles") or []
        out = []
        for b in raw:
            out.append({"time": b.get("time") or b.get("t"),
                        "open": float(b["open"]), "high": float(b["high"]),
                        "low": float(b["low"]), "close": float(b["close"])})
        return out or None
    except Exception:
        return None


_YAHOO_SYM = {"EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
              "AUDUSD": "AUDUSD=X", "USDCAD": "USDCAD=X", "XAUUSD": "GC=F",
              "XAGUSD": "SI=F", "BTCUSD": "BTC-USD"}


def _from_yahoo(symbol, timeframe, count):
    """Real OHLC from Yahoo Finance chart API (public, no key)."""
    import ssl
    sym = _YAHOO_SYM.get(symbol.upper())
    if not sym:
        return None
    tf = {"M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m",
          "H1": "1h", "H4": "1h", "D1": "1d"}.get(timeframe, "1h")
    rng = {"1m": "5d", "5m": "1mo", "15m": "1mo", "30m": "1mo",
           "1h": "3mo", "1d": "2y"}.get(tf, "3mo")
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/%s"
           "?range=%s&interval=%s" % (sym, rng, tf))
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(r, timeout=12, context=ctx) as x:
            d = json.loads(x.read().decode())
        res = (d.get("chart") or {}).get("result") or []
        if not res:
            return None
        q = res[0]["indicators"]["quote"][0]
        ts = res[0].get("timestamp") or []
        out = []
        for i, t in enumerate(ts):
            o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
            if None in (o, h, l, c):
                continue
            out.append({"time": t, "open": round(o, 6), "high": round(h, 6),
                        "low": round(l, 6), "close": round(c, 6)})
        return out[-count:] if out else None
    except Exception:
        return None


def _from_cache(symbol, timeframe):
    p = _cache_path(symbol, timeframe)
    if not os.path.exists(p):
        return None
    try:
        d = json.load(open(p))
        if d.get("source") == "synthetic":
            return None            # never serve synthetic as real
        return d.get("bars") or None
    except Exception:
        return None


def _synthetic(symbol, timeframe, count, seed=None):
    rnd = random.Random(seed if seed is not None else (hash(symbol) & 0xFFFFFFFF))
    px = 1.10 if "USD" in symbol[:3] else 1.0
    bars = []
    for i in range(count):
        drift = rnd.gauss(0, 0.0012)
        o = px
        c = max(0.0001, o + drift)
        hi = max(o, c) + abs(rnd.gauss(0, 0.0004))
        lo = min(o, c) - abs(rnd.gauss(0, 0.0004))
        bars.append({"time": int(time.time()) - (count - i) * 3600,
                     "open": round(o, 6), "high": round(hi, 6),
                     "low": round(lo, 6), "close": round(c, 6)})
        px = c
    return bars


def load(symbol, timeframe="H1", count=400, allow_synthetic=True):
    """Return (bars, source) where source in {"bridge","cache","synthetic"}."""
    b = _from_bridge(symbol, timeframe, count)
    if b and len(b) >= 120:
        json.dump({"symbol": symbol, "timeframe": timeframe, "bars": b,
                   "fetched": time.time(), "source": "bridge"},
                  open(_cache_path(symbol, timeframe), "w"))
        return b, "bridge"
    y = _from_yahoo(symbol, timeframe, count)
    if y and len(y) >= 120:
        json.dump({"symbol": symbol, "timeframe": timeframe, "bars": y,
                   "fetched": time.time(), "source": "yahoo"},
                  open(_cache_path(symbol, timeframe), "w"))
        return y, "yahoo"
    c = _from_cache(symbol, timeframe)
    if c and len(c) >= 120:
        return c, "cache"
    if allow_synthetic:
        # NEVER cache synthetic bars - they must not masquerade as real later.
        s = _synthetic(symbol, timeframe, count)
        return s, "synthetic"
    return [], "none"


def is_real(source: str) -> bool:
    return source in ("bridge", "cache", "yahoo")


if __name__ == "__main__":
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "EURUSD"
    bars, src = load(sym, allow_synthetic=True)
    print("%s: %d bars from %s (real=%s)" % (sym, len(bars), src, is_real(src)), flush=True)
    try:
        from edge import evaluate
    except ImportError:
        from fxintel.edge import evaluate
    rs = evaluate(sym, bars)
    print("  strategies evaluated: %d" % len(rs), flush=True)
    for r in rs:
        print("  %-9s trades=%-3d wr=%.0f%% exp=%+.3fR pf=%.2f %s"
              % (r.strategy, r.trades, r.win_rate * 100, r.expectancy_R, r.profit_factor,
                 "APPROVED" if r.approved else r.reason), flush=True)
