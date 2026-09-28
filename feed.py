"""Price feed: OHLC candles for FX/metals via Yahoo Finance chart API.
Zero external deps (stdlib only). Falls back across hosts."""
import json, urllib.request, urllib.error, time

YAHOO_HOSTS = ["https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com"]
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

def yahoo_symbol(sym: str) -> str:
    # EURUSD -> EURUSD=X ; XAUUSD -> GC=F ; fallback passthrough
    s = sym.upper().replace("+", "")
    special = {"XAUUSD": "GC=F", "XAGUSD": "SI=F", "USOIL": "CL=F", "WTI": "CL=F"}
    return special.get(s, s + "=X" if len(s) == 6 else s)

def candles(sym: str, interval="1h", rng="5d"):
    """Return list of dicts: {t,o,h,l,c} oldest->newest."""
    y = yahoo_symbol(sym)
    path = f"/v8/finance/chart/{y}?range={rng}&interval={interval}"
    last = None
    for host in YAHOO_HOSTS:
        try:
            req = urllib.request.Request(host + path, headers=UA)
            with urllib.request.urlopen(req, timeout=12) as r:
                data = json.load(r)
            res = data["chart"]["result"][0]
            ts = res["timestamp"]
            q = res["indicators"]["quote"][0]
            out = []
            for i, t in enumerate(ts):
                if q["close"][i] is None:
                    continue
                out.append({"t": t, "o": q["open"][i], "h": q["high"][i],
                            "l": q["low"][i], "c": q["close"][i]})
            if out:
                return out
        except Exception as e:
            last = e
            continue
    raise RuntimeError(f"feed failed for {sym}: {last}")

def last_price(sym: str):
    c = candles(sym, interval="5m", rng="1d")
    return c[-1]["c"]
