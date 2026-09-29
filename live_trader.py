#!/usr/bin/env python3
"""LIVE risk-governed trading loop (production).

Difference from auto_trader.py: this talks to a REAL MT5 HTTP bridge
(config/mt5.json) instead of the simulator. The RiskGovernor is identical, so
paper and live behaviour match exactly. Hard safety rails that CANNOT be
bypassed by strategy code:

  * config/mt5.json missing OR preflight fails -> do nothing (fail-closed)
  * risk <=1.5%/order, mandatory stop, R:R>=1.5, aggregate open risk <=4%
  * DAILY LOSS LIMIT: if equity falls >=5% from the day's start -> halt for the day
  * KILL SWITCH file trading/DISABLE_LIVE (or env MT5_KILL=1) -> instant halt
  * LIVE flag in config must be explicitly true; default false = dry-run only

Usage:
  python3 live_trader.py --preflight      # validate bridge, no orders
  python3 live_trader.py --once           # one governed cycle
  python3 live_trader.py --dry-run        # full pipeline, no orders sent
"""
from __future__ import annotations
import argparse, json, os, sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mt5_bridge import (RiskGovernor, Rules, OrderRequest, execute,
                        load_http_broker, HttpMT5Broker, SimBroker, pip_size)
from fxintel.signals import build_plan
from fxintel.bars import load as load_bars, is_real as bars_are_real
from fxintel.edge import best as edge_best
from mt5_relay import LedgerMT5Broker, live_broker_from_env

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "config", "mt5.json")
KILL = os.path.join(HERE, "DISABLE_LIVE")
STATE = os.path.join(HERE, "reports", "live_state.json")
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD"]
DAILY_LOSS_LIMIT_PCT = 5.0
# HARD pre-trade gate: a live order is placed ONLY if the strategy shows
# positive out-of-sample expectancy on REAL bars for that symbol.
EDGE_GATE = os.environ.get("EDGE_GATE", "1") != "0"
EDGE_MIN_EXP = float(os.environ.get("EDGE_MIN_EXP", "0.03"))


def halted():
    if os.environ.get("MT5_KILL") == "1":
        return True, "env MT5_KILL=1"
    if os.path.exists(KILL):
        return True, f"kill-switch file present: {KILL}"
    return False, ""


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {"day": None, "day_start_equity": None, "halted_today": False, "orders": []}


def save_state(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w") as f:
        json.dump(s, f, indent=1)


def make_broker(cfg):
    mode = cfg.get("mode", "relay")
    if mode == "sim":
        return SimBroker(equity=cfg.get("equity", 10000.0))
    if mode == "relay":
        # Real path: local cost-meter ledger (:4790) relayed to Windows MT5 bridge
        return LedgerMT5Broker(cfg.get("ledger_url") or os.environ.get("LEDGER_URL", "http://127.0.0.1:4790"),
                               cfg.get("ledger_token") or os.environ.get("LEDGER_TOKEN", "change-me-shared-secret"))
    return load_http_broker(CFG)


def preflight(cfg):
    try:
        b = make_broker(cfg)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    try:
        acct = b.account()
        px = b.price("EURUSD")
        return {"ok": True, "account": acct, "EURUSD": px}
    except Exception as e:
        return {"ok": False, "error": "reachable but bad response: %s" % e}


def cycle(dry_run=True):
    st = load_state()
    kill, why = halted()
    if kill:
        print("HALTED:", why)
        return st
    if not os.path.exists(CFG):
        print("no config/mt5.json — nothing to do (fail-closed). "
              "Copy config/mt5.example.json and fill base_url.")
        return st
    with open(CFG) as f:
        cfg = json.load(f)
    live = bool(cfg.get("live", False)) and not dry_run
    pf = preflight(cfg)
    if not pf.get("ok"):
        print("preflight FAILED -> no orders:", pf.get("error"))
        return st

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if st.get("day") != today:
        st = {"day": today, "day_start_equity": pf["account"]["equity"],
              "halted_today": False, "orders": st.get("orders", [])[-200:]}

    eq_now = pf["account"]["equity"]
    dd = (st["day_start_equity"] - eq_now) / max(st["day_start_equity"], 1e-9) * 100
    if dd >= DAILY_LOSS_LIMIT_PCT:
        st["halted_today"] = True
    if st["halted_today"]:
        print(f"daily loss limit hit ({dd:.2f}% >= {DAILY_LOSS_LIMIT_PCT}%) — halt for today")
        save_state(st)
        return st

    gov = RiskGovernor(Rules())
    broker = make_broker(cfg)
    placed = 0
    for sym in SYMBOLS:
        # Real OHLC bars (bridge -> yahoo -> cache); no synthetic for live.
        try:
            raw, bsrc = load_bars(sym, "H1", 400, allow_synthetic=False)
        except Exception:
            raw, bsrc = [], "none"
        if not raw or not bars_are_real(bsrc):
            st["orders"].append({"ts": datetime.now(timezone.utc).isoformat(),
                                 "sym": sym, "skipped": "no real bars (%s)" % bsrc})
            print("SKIP %-7s no real bars (%s)" % (sym, bsrc))
            continue
        # Normalize to the h/l/c/o shape the signal + indicator modules expect.
        bars = [{"o": b.get("open", b.get("o")), "h": b.get("high", b.get("h")),
                 "l": b.get("low", b.get("l")), "c": b.get("close", b.get("c")),
                 "time": b.get("time")} for b in raw]
        # Intel dict for the signal engine (trend/regime/vol/flow/price).
        intel = {}
        closes = [b["c"] for b in bars]
        try:
            from fxintel.indicators import ema as _ema, rsi as _rsi, atr as _atr_raw, adx as _adx_raw
            e20 = (_ema(closes, 20) or [None])[-1]
            e50 = (_ema(closes, 50) or [None])[-1]
            e200 = (_ema(closes, 200) or [None])[-1]
            rsi_v = (_rsi(closes, 14) or [None])[-1]
            atr_v = (_atr_raw(bars, 14) or [None])[-1]
            adx_v = (_adx_raw(bars, 14) or [None])[-1]
            intel["trend"] = "up" if (e20 and e50 and e20 > e50) else ("down" if (e20 and e50) else "flat")
            intel["_ema_trend"] = intel["trend"]
        except Exception:
            e20 = e50 = e200 = rsi_v = atr_v = adx_v = None
            intel["trend"] = "flat"
        # Real regime from scalars (fail-soft to "unknown").
        try:
            from fxintel.regime import classify as _regime_classify
            _rg = _regime_classify(bars[-1]["c"], e20, e50, e200, rsi_v, adx_v, atr_v)
            intel["regime"] = (_rg.get("trend") if isinstance(_rg, dict) else _rg) or "unknown"
        except Exception:
            intel["regime"] = "unknown"
        # REAL money flow (MFI/CMF/RVOL -> flow_score in [-100,100]).
        try:
            from fxintel import moneyflow as _mf
            ana = _mf.analyze(bars)
            intel["flow_score"] = float(ana.get("flow_score") or 0.0)
            intel["moneyflow"] = ana
        except Exception:
            intel["flow_score"] = 0.0
        intel["vol_state"] = "normal"
        intel["price"] = bars[-1]["c"]
        try:
            plan = build_plan(sym, bars, intel, equity_usd=eq_now, risk_pct=1.5)
        except Exception as e:
            st["orders"].append({"ts": datetime.now(timezone.utc).isoformat(),
                                 "sym": sym, "skipped": "plan error: %s" % e})
            continue
        if not getattr(plan, "valid", False):
            print("SKIP %-7s plan invalid (%s)" % (sym, getattr(plan, "rationale", "")[:40]))
            continue
        direction = getattr(plan, "direction", "").lower()
        if direction not in ("buy", "sell"):
            continue

        # --- EDGE GATE (hard): must show OOS positive expectancy on real bars ---
        edge_ok, edge_note, edge_rep = True, "gate off", None
        if EDGE_GATE:
            bars, src = load_bars(sym, "H1", 400, allow_synthetic=False)
            if not bars or not bars_are_real(src):
                edge_ok, edge_note = False, "no real bars (%s)" % src
            else:
                er = edge_best(sym, bars, min_expectancy_R=EDGE_MIN_EXP)
                edge_rep = er.to_dict()
                edge_ok = bool(er.approved)
                edge_note = "%s %s trades=%d exp=%+.3fR pf=%.2f" % (
                    er.strategy, "APPROVED" if er.approved else "REJECT",
                    er.trades, er.expectancy_R, er.profit_factor)
        st.setdefault("edge", {})[sym] = {"ok": edge_ok, "note": edge_note, "report": edge_rep}
        print("EDGE %-7s %s | %s" % (sym, "PASS" if edge_ok else "BLOCK", edge_note))
        if not edge_ok:
            st["orders"].append({"ts": datetime.now(timezone.utc).isoformat(),
                                 "sym": sym, "edge_blocked": True, "note": edge_note})
            continue

        px = broker.price(sym)
        pip = pip_size(sym)
        stop = px - 20 * pip if direction == "buy" else px + 20 * pip
        tgt = px + 45 * pip if direction == "buy" else px - 45 * pip
        req = OrderRequest(symbol=sym, direction=direction, entry=round(px, 5),
                           stop=round(stop, 5), target=round(tgt, 5),
                           equity=eq_now, open_risk_pct=0.0, comment="live-governed")
        if not live:
            rec = {"ts": datetime.now(timezone.utc).isoformat(), "sym": sym,
                   "direction": direction, "dry_run": True,
                   "would_risk_pct": 1.5}
            st["orders"].append(rec)
            print(f"DRY-RUN {sym} {direction} @ {px:.5f} stop {stop:.5f} tgt {tgt:.5f}")
            continue
        out = execute(broker, req, gov)
        st["orders"].append({"ts": out["ts"], "sym": sym, "direction": direction,
                             "result": out["result"], "decision": out["decision"]})
        if out["result"] == "placed":
            placed += 1
    save_state(st)
    print(f"cycle done: {placed} live orders placed (live={live})")
    return st


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.preflight:
        if not os.path.exists(CFG):
            print("no config/mt5.json"); raise SystemExit(0)
        with open(CFG) as f:
            print(json.dumps(preflight(json.load(f)), indent=1))
    else:
        cycle(dry_run=not (a.once and not a.dry_run))
