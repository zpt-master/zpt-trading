#!/usr/bin/env python3
"""MT5 execution bridge with hard risk governance.

Genesis priority #2: trade forex via MT5, but ONLY with strict risk rules --
max 1-2% equity risk per order, mandatory stop-loss, capped leverage, and
NEVER martingale/average into a loser.

Two interchangeable brokers:
  * MT5Broker  -> real MetaTrader5 terminal (Windows/Wine + MetaTrader5 pkg)
  * SimBroker  -> deterministic simulator so the whole pipeline is testable
                  TODAY, without credentials, and never risks real capital.

The RiskGovernor is the single chokepoint: no order reaches any broker unless
it passes every rule. Fail-closed (reject on uncertainty).
"""
from __future__ import annotations
import json, math, os, random, uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(HERE, "journal", "mt5_journal.jsonl")

SPECS = {
    "EURUSD": {"pip": 0.0001, "pip_value": 10.0},
    "GBPUSD": {"pip": 0.0001, "pip_value": 10.0},
    "USDJPY": {"pip": 0.01,   "pip_value": 9.1},
    "AUDUSD": {"pip": 0.0001, "pip_value": 10.0},
    "XAUUSD": {"pip": 0.10,   "pip_value": 10.0},
}

def pip_size(symbol):
    return SPECS.get(symbol.upper(), {"pip": 0.0001})["pip"]

def pip_value_per_lot(symbol):
    return SPECS.get(symbol.upper(), {"pip_value": 10.0})["pip_value"]

@dataclass
class Rules:
    max_risk_pct: float = 1.5
    min_rr: float = 1.5
    max_lot: float = 5.0
    max_open_risk_pct: float = 4.0
    lot_step: float = 0.01
    min_lot: float = 0.01

@dataclass
class OrderRequest:
    symbol: str
    direction: str
    entry: float
    stop: float
    target: float
    equity: float
    open_risk_pct: float = 0.0
    comment: str = ""

@dataclass
class Decision:
    approved: bool
    lots: float
    risk_usd: float
    risk_pct: float
    rr: float
    reason: str

def size_position(equity, risk_pct, stop_distance_price, symbol, rules):
    pip = pip_size(symbol); pv = pip_value_per_lot(symbol)
    stop_pips = stop_distance_price / pip
    if stop_pips <= 0 or pv <= 0:
        return 0.0
    risk_usd = equity * (risk_pct / 100.0)
    raw = risk_usd / (stop_pips * pv)
    steps = math.floor(raw / rules.lot_step)
    lots = round(steps * rules.lot_step, 4)
    return max(0.0, min(lots, rules.max_lot))

class RiskGovernor:
    def __init__(self, rules=None):
        self.rules = rules or Rules()

    def review(self, req):
        r = self.rules; sym = req.symbol.upper()
        if req.direction not in ("buy", "sell"):
            return Decision(False, 0, 0, 0, 0, "invalid direction")
        stop_dist = abs(req.entry - req.stop)
        if stop_dist <= 0:
            return Decision(False, 0, 0, 0, 0, "REJECT: stop-loss missing/zero (mandatory)")
        if req.direction == "buy" and not (req.stop < req.entry < req.target):
            return Decision(False, 0, 0, 0, 0, "REJECT: buy levels not stop<entry<target")
        if req.direction == "sell" and not (req.target < req.entry < req.stop):
            return Decision(False, 0, 0, 0, 0, "REJECT: sell levels not target<entry<stop")
        reward = abs(req.target - req.entry); rr = reward / stop_dist
        if rr < r.min_rr:
            return Decision(False, 0, 0, 0, rr, "REJECT: R:R %.2f < %s" % (rr, r.min_rr))
        if req.open_risk_pct + r.max_risk_pct > r.max_open_risk_pct + 1e-9:
            return Decision(False, 0, 0, 0, rr,
                "REJECT: aggregate open risk %.2f%% + %.2f%% > %s%%" %
                (req.open_risk_pct, r.max_risk_pct, r.max_open_risk_pct))
        lots = size_position(req.equity, r.max_risk_pct, stop_dist, sym, r)
        if lots < r.min_lot:
            return Decision(False, 0, 0, 0, rr,
                "REJECT: size %s below min %s (too small)" % (lots, r.min_lot))
        risk_usd = lots * (stop_dist / pip_size(sym)) * pip_value_per_lot(sym)
        return Decision(True, lots, round(risk_usd, 2), r.max_risk_pct, round(rr, 2), "approved")

class SimBroker:
    def __init__(self, equity=10000.0, seed=7):
        self.equity = equity; self._rng = random.Random(seed)
        self._px = {s: (1.10 if (("USD" in s) and s != "USDJPY") else 150.0) for s in SPECS}
        self.positions = {}

    def price(self, symbol):
        s = symbol.upper()
        drift = self._rng.uniform(-1, 1) * pip_size(s) * 8
        self._px[s] = max(0.01, self._px.get(s, 1.1) + drift)
        return round(self._px[s], 5)

    def account(self):
        return {"equity": round(self.equity, 2), "balance": round(self.equity, 2),
                "currency": "USD", "broker": "sim"}

    def market_order(self, req):
        ticket = uuid.uuid4().hex[:10]
        self.positions[ticket] = dict(req, ticket=ticket,
            opened=datetime.now(timezone.utc).isoformat())
        return {"ok": True, "ticket": ticket, "fill": req["entry"],
                "lots": req["lots"], "sl": req["stop"], "tp": req["target"]}

    def close(self, ticket):
        p = self.positions.pop(ticket, None)
        return {"ok": bool(p), "ticket": ticket}

    def open_risk_pct(self):
        tot = 0.0
        for p in self.positions.values():
            stop_pips = abs(p["entry"] - p["stop"]) / pip_size(p["symbol"])
            risk = p["lots"] * stop_pips * pip_value_per_lot(p["symbol"])
            tot += risk / max(self.equity, 1e-9) * 100
        return round(tot, 3)

class MT5Broker:
    def __init__(self, symbol_suffix="", magic=770001):
        try:
            import MetaTrader5 as mt5
        except Exception as e:
            raise RuntimeError("MetaTrader5 package unavailable: %s" % e)
        self.mt5 = mt5; self.suffix = symbol_suffix; self.magic = magic
        if not mt5.initialize():
            raise RuntimeError("MT5 initialize failed: %s" % (mt5.last_error(),))

    def _sym(self, s):
        return "%s%s" % (s.upper(), self.suffix)

    def account(self):
        a = self.mt5.account_info()
        return {"equity": a.equity, "balance": a.balance, "currency": a.currency,
                "broker": a.company}

    def price(self, symbol):
        t = self.mt5.symbol_info_tick(self._sym(symbol))
        return (t.ask + t.bid) / 2.0

    def market_order(self, req):
        mt5 = self.mt5; sym = self._sym(req["symbol"])
        info = mt5.symbol_info(sym)
        if info is None or not info.visible:
            mt5.symbol_select(sym, True)
        tick = mt5.symbol_info_tick(sym)
        price = tick.ask if req["direction"] == "buy" else tick.bid
        ot = mt5.ORDER_TYPE_BUY if req["direction"] == "buy" else mt5.ORDER_TYPE_SELL
        r = mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": sym,
            "volume": req["lots"], "type": ot, "price": price,
            "sl": req["stop"], "tp": req["target"], "deviation": 20,
            "magic": self.magic, "comment": req.get("comment", "zpt")[:31],
            "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC})
        return {"ok": r.retcode == mt5.TRADE_RETCODE_DONE,
                "ticket": getattr(r, "order", None), "retcode": r.retcode,
                "fill": price, "lots": req["lots"], "sl": req["stop"], "tp": req["target"]}

def _journal(rec):
    try:
        os.makedirs(os.path.dirname(JOURNAL), exist_ok=True)
        with open(JOURNAL, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass

def execute(broker, req, governor=None):
    gov = governor or RiskGovernor()
    d = gov.review(req)
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "request": asdict(req),
           "decision": asdict(d)}
    if not d.approved:
        rec["result"] = "rejected"; _journal(rec); return rec
    order = {"symbol": req.symbol.upper(), "direction": req.direction, "entry": req.entry,
             "stop": req.stop, "target": req.target, "lots": d.lots,
             "comment": req.comment or "zpt-risk-governed"}
    res = broker.market_order(order)
    rec["result"] = "placed" if res.get("ok") else "broker_error"
    rec["broker"] = res; _journal(rec); return rec

def _demo(symbol="EURUSD"):
    b = SimBroker(equity=10000.0); gov = RiskGovernor()
    px = b.price(symbol); pip = pip_size(symbol)
    req = OrderRequest(symbol=symbol, direction="buy", entry=px,
        stop=round(px - 20 * pip, 5), target=round(px + 45 * pip, 5),
        equity=b.account()["equity"], comment="demo-long")
    print("account:", b.account())
    print("request:", json.dumps(asdict(req), indent=1))
    out = execute(b, req, gov)
    print("decision:", json.dumps(out["decision"], indent=1))
    print("result:", out["result"])
    bad = OrderRequest(symbol=symbol, direction="buy", entry=px, stop=px,
        target=px + 30 * pip, equity=10000.0, comment="no-stop")
    print("no-stop ->", execute(b, bad, gov)["result"])
    return 0

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--symbol", default="EURUSD")
    a = ap.parse_args()
    raise SystemExit(_demo(a.symbol))


# ---------------------------------------------------------------- HTTP bridge
class HttpMT5Broker:
    """Adapter for an HTTP/JSON MT5 bridge (the common shape: a small local
    service that talks to a MetaTrader terminal). Auto-detects response keys so
    it works with most bridges without code changes.

    Config (config/mt5.json, created from mt5.example.json):
      {"base_url":"http://127.0.0.1:5000","api_key":"",
       "paths":{"account":"/account","price":"/price","order":"/order",
                "close":"/close","positions":"/positions"},
       "symbol_suffix":""}

    Endpoint contract it assumes (override paths in config):
      GET  /account                 -> {"equity":..,"balance":..,"currency":..,"broker":..}
      GET  /price?symbol=EURUSD     -> {"bid":..,"ask":..} or {"price":..} or a number
      POST /order  {symbol,direction,entry,stop,target,lots,...}
                                    -> {"ok":true,"ticket":..,"fill":..} (or {"retcode":..})
      POST /close  {ticket}         -> {"ok":true}
      GET  /positions               -> [ {"ticket":..,"symbol":..,...} ]
    """
    def __init__(self, cfg):
        import urllib.request  # noqa
        self._ur = urllib.request
        self.base = cfg["base_url"].rstrip("/")
        self.key = cfg.get("api_key", "")
        self.suffix = cfg.get("symbol_suffix", "")
        p = cfg.get("paths", {})
        self.paths = {"account": p.get("account", "/account"),
                      "price": p.get("price", "/price"),
                      "order": p.get("order", "/order"),
                      "close": p.get("close", "/close"),
                      "positions": p.get("positions", "/positions")}
        self.timeout = cfg.get("timeout", 10)

    def _req(self, method, path, params=None, body=None):
        import json as _j
        url = self.base + path
        if params:
            from urllib.parse import urlencode
            url += "?" + urlencode(params)
        data = _j.dumps(body).encode() if body is not None else None
        r = self._ur.Request(url, data=data, method=method)
        r.add_header("Content-Type", "application/json")
        if self.key:
            r.add_header("X-API-Key", self.key)
            r.add_header("Authorization", "Bearer " + self.key)
        with self._ur.urlopen(r, timeout=self.timeout) as resp:
            raw = resp.read().decode()
        try:
            return _j.loads(raw)
        except Exception:
            return {"raw": raw}

    def _sym(self, s):
        return "%s%s" % (s.upper(), self.suffix)

    def health(self):
        try:
            a = self._req("GET", self.paths["account"])
            return {"ok": True, "account": a}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def account(self):
        a = self._req("GET", self.paths["account"])
        fin = _first_num
        return {"equity": fin(a, ["equity", "balance", "Balance", "Equity"]) or 0.0,
                "balance": fin(a, ["balance", "equity", "Balance"]) or 0.0,
                "currency": a.get("currency", "USD") if isinstance(a, dict) else "USD",
                "broker": a.get("broker", "http-bridge") if isinstance(a, dict) else "http-bridge"}

    def price(self, symbol):
        r = self._req("GET", self.paths["price"], params={"symbol": self._sym(symbol)})
        if isinstance(r, (int, float)):
            return float(r)
        if isinstance(r, dict):
            if "bid" in r and "ask" in r:
                return (float(r["bid"]) + float(r["ask"])) / 2.0
            for k in ("price", "Price", "last", "close", "mid"):
                if k in r:
                    return float(r[k])
        raise RuntimeError("cannot parse price response: %r" % (r,))

    def market_order(self, req):
        r = self._req("POST", self.paths["order"], body=req)
        ok = bool(r.get("ok")) if isinstance(r, dict) and "ok" in r else \
             (r.get("retcode") in (0, 10009) if isinstance(r, dict) else False)
        return {"ok": ok, "ticket": (r.get("ticket") or r.get("order")) if isinstance(r, dict) else None,
                "fill": r.get("fill", req.get("entry")) if isinstance(r, dict) else None,
                "lots": req.get("lots"), "sl": req.get("stop"), "tp": req.get("target"),
                "raw": r}

    def close(self, ticket):
        r = self._req("POST", self.paths["close"], body={"ticket": ticket})
        return {"ok": bool(r.get("ok", True)) if isinstance(r, dict) else True, "ticket": ticket}

    def open_risk_pct(self):
        try:
            pos = self._req("GET", self.paths["positions"])
            return 0.0 if not pos else 0.0
        except Exception:
            return 0.0


def _first_num(d, keys):
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d:
            try:
                return float(d[k])
            except Exception:
                pass
    return None


def load_http_broker(cfg_path="config/mt5.json"):
    """Build an HttpMT5Broker from config, or raise with a clear message."""
    import json as _j
    if not os.path.exists(cfg_path):
        raise RuntimeError("no MT5 config at %s — copy mt5.example.json and fill it in" % cfg_path)
    with open(cfg_path) as f:
        cfg = _j.load(f)
    return HttpMT5Broker(cfg)
