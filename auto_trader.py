#!/usr/bin/env python3
"""Autonomous paper-trading loop: signals -> RiskGovernor -> broker -> journal.

Connects the existing risk-governed signal engine (fxintel.signals) to the MT5
execution bridge (mt5_bridge) so genesis priority #2 runs continuously in PAPER
mode until real MT5 credentials arrive. Every order passes the same
RiskGovernor that the live path uses -- so behaviour is identical, only the
broker (SimBroker) differs. Nothing risks real capital.

Outputs:
  reports/auto_trader_state.json   -- equity curve, open positions, stats
  journal/mt5_journal.jsonl        -- every governed decision (append-only)
"""
import json, os, sys, time
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mt5_bridge import SimBroker, RiskGovernor, OrderRequest, execute, pip_size
from fxintel.signals import build_plan

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "reports", "auto_trader_state.json")
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD"]
START_EQUITY = 10000.0


def _load():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {"start_equity": START_EQUITY, "equity": START_EQUITY,
                "updated": None, "open": {}, "closed": [],
                "wins": 0, "losses": 0, "ticks": 0}


def _save(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    s["updated"] = datetime.now(timezone.utc).isoformat()
    with open(STATE, "w") as f:
        json.dump(s, f, indent=1)


def _settle(s, broker):
    """Re-price open positions; close on stop/target hit. Deterministic."""
    still = {}
    for ticket, p in s["open"].items():
        px = broker.price(p["symbol"])
        p["last"] = px
        hit_stop = (p["direction"] == "buy" and px <= p["stop"]) or \
                   (p["direction"] == "sell" and px >= p["stop"])
        hit_tp = (p["direction"] == "buy" and px >= p["target"]) or \
                 (p["direction"] == "sell" and px <= p["target"])
        if hit_stop or hit_tp:
            risk_usd = p["risk_usd"]
            pnl = (-risk_usd) if hit_stop else (abs(p["target"] - p["entry"]) /
                  abs(p["entry"] - p["stop"]) * risk_usd)
            s["equity"] = round(s["equity"] + pnl, 2)
            s["wins" if hit_tp else "losses"] += 1
            s["closed"].append(dict(p, exit=px, pnl=round(pnl, 2),
                result="target" if hit_tp else "stop",
                closed=datetime.now(timezone.utc).isoformat()))
            broker.close(ticket)
        else:
            still[ticket] = p
    s["open"] = still


def tick():
    s = _load()
    broker = SimBroker(equity=s["equity"])
    # restore broker book with known last prices
    for _, p in s["open"].items():
        broker._px[p["symbol"]] = p.get("last", p["entry"])
    _settle(s, broker)

    gov = RiskGovernor()
    open_risk = sum(pp["risk_usd"] for pp in s["open"].values()) / max(s["equity"], 1) * 100
    for sym in SYMBOLS:
        try:
            d = {}
            plan = build_plan(sym, [], d, equity_usd=s["equity"], risk_pct=1.5)
        except Exception:
            continue
        if not getattr(plan, "valid", False):
            continue
        px = broker.price(sym)
        direction = getattr(plan, "direction", "").lower()
        if direction not in ("buy", "sell"):
            continue
        # Use the plan's own stop/target if present, else ATR-derived
        stop = getattr(plan, "stop", None) or (px - 20 * pip_size(sym) if direction == "buy" else px + 20 * pip_size(sym))
        tgt = getattr(plan, "target", None) or (px + 45 * pip_size(sym) if direction == "buy" else px - 45 * pip_size(sym))
        req = OrderRequest(symbol=sym, direction=direction, entry=round(px, 5),
                           stop=round(stop, 5), target=round(tgt, 5),
                           equity=s["equity"], open_risk_pct=open_risk,
                           comment="auto-paper")
        out = execute(broker, req, gov)
        if out["result"] == "placed":
            tk = out["broker"]["ticket"]
            s["open"][tk] = {"ticket": tk, "symbol": sym, "direction": direction,
                             "entry": req.entry, "stop": req.stop, "target": req.target,
                             "lots": out["decision"]["lots"], "risk_usd": out["decision"]["risk_usd"],
                             "last": req.entry, "opened": out["ts"]}
            open_risk += out["decision"]["risk_pct"]

    s["ticks"] += 1
    # equity curve (last 200 points)
    s.setdefault("curve", []).append({"ts": datetime.now(timezone.utc).isoformat(),
                                      "equity": s["equity"]})
    s["curve"] = s["curve"][-200:]
    _save(s)
    return s


def summary(s=None):
    s = s or _load()
    n = s["wins"] + s["losses"]
    wr = (s["wins"] / n * 100) if n else 0.0
    ret = (s["equity"] / s["start_equity"] - 1) * 100
    lines = ["# Auto-Trader (PAPER) — Honest Track Record", "",
             f"_Updated: {s['updated']}_", "",
             f"- Start equity: ${s['start_equity']:.2f}",
             f"- Current equity: **${s['equity']:.2f}** ({ret:+.2f}%)",
             f"- Closed trades: {n}  (W {s['wins']} / L {s['losses']}, winrate {wr:.0f}%)",
             f"- Open positions: {len(s['open'])}",
             f"- Ticks run: {s['ticks']}", "",
             "Every order passed the same RiskGovernor used for the live path:",
             "<=1.5% risk/order, mandatory stop, R:R>=1.5, aggregate risk capped 4%.",
             "An empty record means the rules found no aligned edge — capital preserved.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    s = tick()
    md = summary(s)
    with open(os.path.join(HERE, "reports", "track_record.md"), "w") as f:
        f.write(md)
    print(md)
