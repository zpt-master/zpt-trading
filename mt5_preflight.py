#!/usr/bin/env python3
"""Locate a reachable MT5 HTTP bridge and validate it before going live.

Order of attempts:
  1) config/mt5.json if present (explicit)
  2) env vars: MT5_BRIDGE_URL / MT5_API_KEY
  3) common localhost ports + paths

Prints a clear verdict. Never places orders.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mt5_bridge import HttpMT5Broker

CANDIDATE_PORTS = [5000, 5001, 5057, 8000, 8080, 8081, 8090, 9000, 8088, 8091]
CANDIDATE_PATHS = ["/account", "/api/account", "/v1/account", "/health", "/"]


def try_url(base, key=""):
    cfg = {"base_url": base, "api_key": key,
           "paths": {"account": "/account", "price": "/price", "order": "/order",
                     "close": "/close", "positions": "/positions"}}
    b = HttpMT5Broker(cfg)
    for p in CANDIDATE_PATHS:
        try:
            cfg["paths"]["account"] = p
            b.paths["account"] = p
            a = b._req("GET", p)
            if isinstance(a, dict) and any(k in a for k in
                ("equity", "balance", "Balance", "Equity", "account", "status")):
                return {"ok": True, "base": base, "path": p, "sample": a}
        except Exception:
            continue
    return {"ok": False, "base": base}


def main():
    found = []
    # 1) explicit config
    if os.path.exists("config/mt5.json"):
        with open("config/mt5.json") as f:
            cfg = json.load(f)
        b = HttpMT5Broker(cfg)
        h = b.health()
        print("config/mt5.json ->", json.dumps(h)[:200])
        if h.get("ok"):
            found.append(cfg["base_url"])
    # 2) env
    env_url = os.environ.get("MT5_BRIDGE_URL")
    if env_url:
        r = try_url(env_url.rstrip("/"), os.environ.get("MT5_API_KEY", ""))
        print("env MT5_BRIDGE_URL ->", json.dumps(r)[:200])
        if r.get("ok"):
            found.append(env_url)
    # 3) localhost scan
    for port in CANDIDATE_PORTS:
        base = "http://127.0.0.1:%d" % port
        r = try_url(base)
        if r.get("ok"):
            print("FOUND bridge at", base, "path", r["path"], "->", json.dumps(r["sample"])[:160])
            found.append(base)
    if found:
        print("VERDICT: MT5 bridge REACHABLE ->", found[0])
    else:
        print("VERDICT: no MT5 HTTP bridge reachable from this sandbox.")
        print("Set config/mt5.json or env MT5_BRIDGE_URL to the bridge base_url.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
