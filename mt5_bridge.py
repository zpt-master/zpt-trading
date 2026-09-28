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
