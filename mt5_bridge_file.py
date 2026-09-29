#!/usr/bin/env python3
"""mt5_bridge_file.py - file-IPC bridge to the ZptGovEA Expert Advisor.

The EA (mt5/MQL5/Experts/ZptGovEA.mq5) runs inside MT5 and enforces the risk
governor broker-side. This module is the Python half:

  push_signals(plans) -> write zpt_signals.csv into MT5 Common\\Files
  read_state()        -> read zpt_state.json (equity/positions/agg risk)
  settle(day)         -> reconcile payouts vs the HWM (1 USD = 100 cents)

Common\\Files location is auto-detected per-OS; override with MT5_COMMON.
Only VALID governed plans (stop>0, rr>=1.5) are ever pushed.
"""
from __future__ import annotations
import os, sys, csv, json, glob, time, datetime as dt

ROWS = ("symbol", "side", "entry", "stop", "target", "lots")


def common_dir() -> str:
    env = os.environ.get("MT5_COMMON")
    if env:
        return env
    cands = []
    home = os.path.expanduser("~")
    cands += glob.glob(os.path.join(home, ".wine", "drive_c", "Program Files*", "*MT5*", "MQL5", "Files"))
    cands += glob.glob("C:/Users/*/AppData/Roaming/MetaQuotes/Terminal/Common/Files")
    cands += [os.path.join(home, ".mt5", "Common", "Files")]
    for c in cands:
        if os.path.isdir(c):
            return c
    return os.path.join(os.getcwd(), "mt5", "MQL5", "Files")


def _valid(p: dict) -> bool:
    try:
        if not p.get("valid"):
            return False
        stop = float(p.get("stop") or 0)
        entry = float(p.get("entry") or 0)
        tgt = float(p.get("target") or 0)
        rr = abs(tgt - entry) / abs(entry - stop) if abs(entry - stop) > 0 else 0
        return stop > 0 and rr >= 1.5 and float(p.get("size_lots") or 0) > 0
    except Exception:
        return False


def push_signals(plans, dry=True) -> int:
    """Write only governed-valid plans to the EA's signal file. Returns count."""
    good = [p for p in plans if _valid(p)]
    if not good:
        return 0
    d = common_dir()
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "zpt_signals.csv")
    tmp = path + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["# zptmaster governed signals", dt.datetime.utcnow().isoformat() + "Z",
                    "dry" if dry else "live"])
        for p in good:
            w.writerow([str(p.get("symbol", "")).upper(), str(p.get("side", "")).upper(),
                        p.get("entry", 0), p.get("stop", 0), p.get("target", 0), p.get("size_lots", 0)])
    os.replace(tmp, path)
    return len(good)


def read_state() -> dict:
    d = common_dir()
    for p in (os.path.join(d, "zpt_state.json"), os.path.join(d, "..", "zpt_state.json")):
        try:
            return json.load(open(p))
        except Exception:
            continue
    return {}


def settle(day: str, hwm: float, equity: float, usd_per_unit_cents: int = 100) -> dict:
    """Daily settlement: profit vs HWM. Losses never lower the HWM."""
    profit_units = equity - hwm
    new_hwm = max(hwm, equity)
    payout_cents = int(round(max(0.0, profit_units) * usd_per_unit_cents))
    return {"day": day, "hwm_before": round(hwm, 2), "equity": round(equity, 2),
            "profit_units": round(profit_units, 2), "payout_cents": payout_cents,
            "hwm_after": round(new_hwm, 2), "paid": payout_cents > 0}


if __name__ == "__main__":
    c = common_dir()
    print("common_dir:", c)
    st = read_state()
    print("state:", json.dumps(st) if st else "(no broker state yet - EA not running)")
    # demo a governed push from the journal
    plans = []
    jp = "journal/plans.jsonl"
    if os.path.exists(jp):
        for line in open(jp).read().splitlines()[-50:]:
            try:
                plans.append(json.loads(line))
            except Exception:
                pass
    n = push_signals(plans, dry=True)
    print(f"pushed {n} governed-valid signals (of {len(plans)} recent)")
    if n == 0:
        print("(expected: engine correctly standing aside - no aligned conviction)")
