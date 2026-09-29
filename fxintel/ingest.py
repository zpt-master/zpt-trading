#!/usr/bin/env python3
"""fxintel/ingest.py - turn ANY dropped data file into datastore JSONL.

The free HTTP feeds are rate-limited; the reliable path to a real 2-year history
is a file: MT5 "Export history" CSV, Dukascopy CSV, or any Date,Open,High,Low,Close.
This module auto-detects the format and writes fxintel/data/<SYM>_<TF>.jsonl so the
backtester and EA research never depend on a flaky network again.

CLI:
  python3 -m fxintel.ingest drop.csv --symbol XAUUSD --tf 1h
  python3 -m fxintel.ingest --scan            # ingest every file in fxintel/inbox/
Formats auto-detected: MT5 tab/semicolon CSV, ISO datetime or epoch, Dukascopy, JSONL.
"""
from __future__ import annotations
import os, sys, json, csv, io, datetime as dt, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data"); os.makedirs(DATA, exist_ok=True)
INBOX = os.path.join(HERE, "inbox"); os.makedirs(INBOX, exist_ok=True)


def _ts(v):
    v = str(v).strip().strip('"')
    if v.replace(".", "", 1).isdigit():
        x = float(v)
        if x > 1e12: x /= 1000.0           # ms epoch
        return int(x)
    for f in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M:%S",
              "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y.%m.%d", "%d.%m.%Y %H:%M",
              "%d.%m.%Y", "%Y/%m/%d %H:%M"):
        try:
            return int(dt.datetime.strptime(v, f).replace(tzinfo=dt.timezone.utc).timestamp())
        except Exception:
            pass
    try:
        return int(dt.datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp())
    except Exception:
        return None


def _rows_from_text(text):
    """Return list of dicts {t,o,h,l,c} from arbitrary CSV/TSV text."""
    # sniff delimiter
    head = text[:2000]
    for delim in ("\t", ";", ",", "|"):
        if delim in head:
            break
    rdr = csv.reader(io.StringIO(text), delimiter=delim)
    rows = [r for r in rdr if r and any(x.strip() for x in r)]
    if not rows:
        return []
    # find header
    hdr = [c.strip().lower().strip('<>') for c in rows[0]]
    def idx(names):
        for n in names:
            for i, c in enumerate(hdr):
                if c == n or c.startswith(n):
                    return i
        return None
    i_t = idx(["datetime", "date", "time", "timestamp"])
    i_o = idx(["open"]); i_h = idx(["high"]); i_l = idx(["low"]); i_c = idx(["close", "last"])
    data = rows[1:]
    if None in (i_o, i_h, i_l, i_c):
        # headerless MT5: Date Time Open High Low Close ...
        data = rows
        # MT5 headerless has date & time in two columns -> 8 cols
        def grab(r):
            if len(r) >= 7:
                t = _ts(r[0] + " " + r[1])
                return t, r[2], r[3], r[4], r[5]
            if len(r) >= 5:
                t = _ts(r[0])
                return t, r[1], r[2], r[3], r[4]
            return None, None, None, None, None
    else:
        def grab(r):
            if i_t is None:
                return None, None, None, None, None
            # if date and next col is time
            t = _ts(r[i_t])
            if t is None and i_t + 1 < len(r):
                t = _ts(r[i_t] + " " + r[i_t + 1])
            return t, r[i_o], r[i_h], r[i_l], r[i_c]
    out = []
    for r in data:
        try:
            t, o, h, l, c = grab(r)
            if t is None:
                continue
            o, h, l, c = float(str(o).replace(",", ".")), float(str(h).replace(",", ".")), \
                         float(str(l).replace(",", ".")), float(str(c).replace(",", "."))
            if not (l <= o <= h and l <= c <= h):
                continue
            out.append({"t": int(t), "o": o, "h": h, "l": l, "c": c})
        except Exception:
            continue
    out.sort(key=lambda x: x["t"])
    ded = []
    for b in out:
        if ded and b["t"] == ded[-1]["t"]:
            continue
        ded.append(b)
    return ded


def ingest(path, symbol, tf):
    text = open(path, "rb").read().decode("utf-8", "replace")
    bars = []
    if path.endswith(".jsonl"):
        for line in text.splitlines():
            if line.strip():
                try: bars.append(json.loads(line))
                except Exception: pass
    elif path.endswith(".json"):
        d = json.loads(text)
        arr = d if isinstance(d, list) else (d.get("bars") or d.get("data") or [])
        for b in arr:
            o = b.get("o", b.get("open")); h = b.get("h", b.get("high"))
            l = b.get("l", b.get("low")); c = b.get("c", b.get("close")); t = b.get("t", b.get("time"))
            if None not in (o, h, l, c, t):
                bars.append({"t": int(_ts(t) or t), "o": float(o), "h": float(h), "l": float(l), "c": float(c)})
    else:
        bars = _rows_from_text(text)
    if not bars:
        return {"ok": False, "path": path, "bars": 0}
    jl = os.path.join(DATA, f"{symbol}_{tf}.jsonl")
    with open(jl, "w") as f:
        for b in bars:
            f.write(json.dumps(b) + "\n")
    meta = {"symbol": symbol, "tf": tf, "bars": len(bars), "source": f"file:{os.path.basename(path)}",
            "period": [dt.datetime.utcfromtimestamp(bars[0]["t"]).strftime("%Y-%m-%d"),
                       dt.datetime.utcfromtimestamp(bars[-1]["t"]).strftime("%Y-%m-%d")],
            "span_days": (bars[-1]["t"] - bars[0]["t"]) // 86400,
            "sha": hashlib.sha256(open(jl, "rb").read()).hexdigest()[:16],
            "ingested": dt.datetime.now(dt.timezone.utc).isoformat()}
    json.dump(meta, open(os.path.join(DATA, f"{symbol}_{tf}.meta.json"), "w"), indent=2)
    return {"ok": True, **meta}


def main(argv):
    if not argv:
        print(__doc__); return 1
    if argv[0] == "--scan":
        n = 0
        for fn in os.listdir(INBOX):
            p = os.path.join(INBOX, fn)
            if not os.path.isfile(p): continue
            sym = fn.split("_")[0].upper() or "UNKNOWN"
            tf = fn.split("_")[1].split(".")[0] if "_" in fn else "1h"
            r = ingest(p, sym, tf); print(json.dumps(r)); n += 1
        print(f"scanned {n} file(s)"); return 0
    path = argv[0]; symbol = "XAUUSD"; tf = "1h"
    if "--symbol" in argv: symbol = argv[argv.index("--symbol") + 1]
    if "--tf" in argv: tf = argv[argv.index("--tf") + 1]
    print(json.dumps(ingest(path, symbol, tf), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
