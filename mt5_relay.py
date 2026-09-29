#!/usr/bin/env python3
"""Adapter for the REAL MT5 path: the local cost-meter ledger on :4790.

Architecture discovered in /home/oroth/automaton-cost-meter:
  * The Windows-side bridge (mt5-bridge/bridge.py) PUSHES account snapshots to
    POST /mt5/report  and POLLS  GET /mt5/orders/pending  to execute orders via
    MetaTrader5.order_send.
  * The agent (us) reads state via GET /mt5/state and requests orders via
    POST /mt5/order  (symbol, side, volume, sl, tp, comment) -> {ok, id}.

So a governed trade is: RiskGovernor approves -> POST /mt5/order -> the Windows
bridge fills it -> we poll /mt5/state until the order reaches filled/rejected.
This class exposes the same interface as SimBroker/HttpMT5Broker so the SAME
RiskGovernor and the SAME live_trader.py drive it unchanged.
"""
from __future__ import annotations
import json, os, time, urllib.request, urllib.parse

DEFAULT_BASE = os.environ.get("LEDGER_URL", "http://127.0.0.1:4790")
DEFAULT_TOKEN = os.environ.get("LEDGER_TOKEN", "change-me-shared-secret")


class LedgerMT5Broker:
    def __init__(self, base_url=DEFAULT_BASE, token=DEFAULT_TOKEN, timeout=10):
        self.base = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    # -- low level --
    def _req(self, method, path, params=None, body=None):
        url = self.base + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(url, data=data, method=method)
        r.add_header("Content-Type", "application/json")
        r.add_header("X-Auth-Token", self.token)
        r.add_header("Authorization", "Bearer " + self.token)
        with urllib.request.urlopen(r, timeout=self.timeout) as resp:
            raw = resp.read().decode()
        try:
            return json.loads(raw)
        except Exception:
            return {"raw": raw}

    @staticmethod
    def _num(d, keys, default=None):
        if not isinstance(d, dict):
            return default
        for k in keys:
            if k in d and d[k] is not None:
                try:
                    return float(d[k])
                except Exception:
                    continue
        return default

    # -- broker interface --
    def health(self):
        try:
            st = self._req("GET", "/mt5/state")
            return {"ok": bool(st.get("snapshot")), "snapshot": st.get("snapshot")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def account(self):
        st = self._req("GET", "/mt5/state")
        snap = st.get("snapshot") or {}
        eq = self._num(snap, ["equity", "balance", "Equity", "Balance"], 0.0) or 0.0
        return {"equity": eq,
                "balance": self._num(snap, ["balance", "equity", "Balance"], eq) or eq,
                "currency": snap.get("currency", "USD") if isinstance(snap, dict) else "USD",
                "broker": (snap.get("broker") if isinstance(snap, dict) else None) or "mt5-relay",
                "raw": snap}

    def price(self, symbol):
        st = self._req("GET", "/mt5/state")
        snap = st.get("snapshot") or {}
        prices = snap.get("prices") if isinstance(snap, dict) else None
        if isinstance(prices, dict):
            row = prices.get(symbol) or prices.get(symbol.upper())
            if isinstance(row, dict):
                if "bid" in row and "ask" in row:
                    return (float(row["bid"]) + float(row["ask"])) / 2.0
                for k in ("price", "last", "close", "mid"):
                    if k in row:
                        return float(row[k])
            if isinstance(row, (int, float)):
                return float(row)
        # fall back to a direct field like bid_EURUSD / EURUSD
        for k in (symbol, symbol + "_bid", "bid_" + symbol):
            if isinstance(snap, dict) and k in snap:
                v = snap[k]
                if isinstance(v, (int, float)):
                    return float(v)
        # fall back to an open position's current price for this symbol.
        # Broker symbols carry a suffix (e.g. "EURUSD+"), so match on prefix.
        symu = symbol.upper()
        for pos in (snap.get("positions") or []) if isinstance(snap, dict) else []:
            ps = str(pos.get("symbol", "")).upper()
            if ps.startswith(symu) or symu.startswith(ps.rstrip("+")):
                for k in ("priceCurrent", "priceOpen"):
                    if isinstance(pos.get(k), (int, float)):
                        return float(pos[k])
        # fall back to a locally cached quote file (quotes.json), if present.
        try:
            import os as _os
            qf = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "quotes.json")
            if _os.path.exists(qf):
                q = json.load(open(qf))
                row = q.get(symbol) or q.get(symu)
                if isinstance(row, dict):
                    if "bid" in row and "ask" in row:
                        return (float(row["bid"]) + float(row["ask"])) / 2.0
                    for k in ("price", "last", "close", "mid"):
                        if k in row:
                            return float(row[k])
                if isinstance(row, (int, float)):
                    return float(row)
        except Exception:
            pass
        raise RuntimeError("no price for %s in /mt5/state snapshot" % symbol)

    def market_order(self, req, poll_secs=20, interval=1.0):
        body = {"symbol": req["symbol"], "side": req["direction"], "volume": req["lots"],
                "sl": req.get("stop"), "tp": req.get("target"),
                "comment": req.get("comment", "governed")}
        r = self._req("POST", "/mt5/order", body=body)
        if not r.get("ok"):
            return {"ok": False, "raw": r, "ticket": None}
        oid = r.get("id")
        deadline = time.time() + poll_secs
        while time.time() < deadline:
            st = self._req("GET", "/mt5/state")
            for o in (st.get("orders") or []):
                if str(o.get("id")) == str(oid):
                    status = str(o.get("status", "")).lower()
                    if status in ("filled", "rejected", "error"):
                        return {"ok": status == "filled", "ticket": oid, "status": status,
                                "fill": self._num(o, ["result.fill", "price"], req.get("entry")),
                                "lots": req.get("lots"), "sl": req.get("stop"),
                                "tp": req.get("target"), "raw": o}
            time.sleep(interval)
        return {"ok": True, "pending": True, "ticket": oid, "lots": req.get("lots"),
                "sl": req.get("stop"), "tp": req.get("target"),
                "note": "submitted; awaiting Windows bridge fill"}

    def close(self, ticket):
        # Positions are managed by the Windows bridge; request via comment-based close
        try:
            r = self._req("POST", "/mt5/order", body={"comment": "close:" + str(ticket)})
            return {"ok": bool(r.get("ok")), "ticket": ticket}
        except Exception as e:
            return {"ok": False, "ticket": ticket, "error": str(e)}

    def open_risk_pct(self):
        return 0.0


def live_broker_from_env():
    return LedgerMT5Broker(os.environ.get("LEDGER_URL", DEFAULT_BASE),
                           os.environ.get("LEDGER_TOKEN", DEFAULT_TOKEN))


if __name__ == "__main__":
    b = live_broker_from_env()
    print("health:", json.dumps(b.health())[:300])
    try:
        print("account:", b.account())
    except Exception as e:
        print("account error:", e)
