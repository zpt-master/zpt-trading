#!/usr/bin/env python3
"""Paper-trading loop for the risk-governed signal engine.

Turns governed plans into a verifiable, HONEST track record (no real money,
no broker). On each tick:
  1. Mark open positions to current price; close at stop (-1R) or target (+rr R).
  2. Open new positions for symbols whose plan is valid and not already held.
  3. Persist state + render reports/track_record.md with performance stats.

This is the proof-of-value artifact: buyers judge a signal product on its
record, not its promises.
"""
import os, json, datetime, math

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "journal", "paper_state.json")
JOURNAL = os.path.join(HERE, "journal", "paper_trades.jsonl")


def _load():
    try:
        return json.load(open(STATE))
    except Exception:
        return {"open": {}, "closed": [], "equity0": 10000.0}


def _save(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(st, open(STATE, "w"), indent=1)


def _log(trade):
    os.makedirs(os.path.dirname(JOURNAL), exist_ok=True)
    open(JOURNAL, "a").write(json.dumps(trade) + "\n")


def _close(pos, price, reason):
    risk = abs(pos["entry"] - pos["stop"])
    if risk <= 0:
        return 0.0
    if pos["side"] == "LONG":
        r = (price - pos["entry"]) / risk
    else:
        r = (pos["entry"] - price) / risk
    trade = dict(pos)
    trade.update({"exit": price, "exit_ts": datetime.datetime.now(datetime.timezone.utc)
                  .isoformat(), "reason": reason, "r_multiple": round(r, 3),
                  "pnl_usd": round(r * pos["risk_usd"], 2)})
    _log(trade)
    return trade


def tick():
    from intel_service import intel, SYMBOLS
    from fxintel.signals import build_plan
    st = _load()
    opened = closed = 0
    for sym in SYMBOLS:
        try:
            d = intel(sym, "1h")
        except Exception:
            continue
        price = d.get("price")
        if price is None:
            bs = d.get("_bars") or []
            price = bs[-1]["c"] if bs else None
        if price is None:
            continue
        pos = st["open"].get(sym)
        if pos:
            hit_stop = (price <= pos["stop"]) if pos["side"] == "LONG" else (price >= pos["stop"])
            hit_tgt = (price >= pos["target"]) if pos["side"] == "LONG" else (price <= pos["target"])
            if hit_stop or hit_tgt:
                t = _close(pos, pos["stop"] if hit_stop else pos["target"],
                           "stop" if hit_stop else "target")
                st["closed"].append(t); del st["open"][sym]; closed += 1
            continue
        p = build_plan(sym, d.get("_bars") or [], d, equity_usd=st["equity0"], risk_pct=1.0)
        if p.valid:
            st["open"][sym] = {"symbol": sym, "side": p.side, "entry": p.entry,
                               "stop": p.stop, "target": p.target, "rr": p.rr,
                               "size_lots": p.size_lots, "risk_usd": p.risk_usd,
                               "open_ts": datetime.datetime.now(datetime.timezone.utc).isoformat()}
            opened += 1
    _save(st)
    stats = summarize(st)
    render(st, stats)
    return {"opened": opened, "closed": closed, "open_now": len(st["open"]), **stats}


def summarize(st):
    cl = st["closed"]
    n = len(cl)
    if n == 0:
        return {"n": 0, "wins": 0, "losses": 0, "win_rate": None,
                "total_R": 0.0, "expectancy_R": None, "pnl_usd": 0.0}
    wins = sum(1 for t in cl if t["r_multiple"] > 0)
    total_r = sum(t["r_multiple"] for t in cl)
    pnl = sum(t["pnl_usd"] for t in cl)
    return {"n": n, "wins": wins, "losses": n - wins,
            "win_rate": round(wins / n, 3), "total_R": round(total_r, 2),
            "expectancy_R": round(total_r / n, 3), "pnl_usd": round(pnl, 2)}


def render(st, stats):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    L = [f"# Paper Track Record — {now}", "",
         "_Risk-governed signal engine, paper-traded (no broker, no real money). "
         "Honest: an empty record means the rules found no edge — which is the point._", "",
         "## Performance", ""]
    if stats["n"] == 0:
        L.append("- No closed trades yet. The engine only trades aligned trend+flow conviction.")
    else:
        L += [f"- Closed trades: **{stats['n']}**  (W {stats['wins']} / L {stats['losses']})",
              f"- Win rate: **{stats['win_rate']}**",
              f"- Total R: **{stats['total_R']}**   Expectancy: **{stats['expectancy_R']} R/trade**",
              f"- P&L (on $10,000 @ 1% risk): **${stats['pnl_usd']}**"]
    L += ["", f"## Open positions ({len(st['open'])})", ""]
    if st["open"]:
        L += ["| Symbol | Side | Entry | Stop | Target | R:R |", "|---|---|---|---|---|---|"]
        for s, p in st["open"].items():
            L.append(f"| {s} | {p['side']} | {p['entry']} | {p['stop']} | {p['target']} | {p['rr']} |")
    else:
        L.append("- None. Standing aside.")
    md = "\n".join(L)
    os.makedirs(os.path.join(HERE, "reports"), exist_ok=True)
    open(os.path.join(HERE, "reports", "track_record.md"), "w").write(md)
    return md


if __name__ == "__main__":
    print(json.dumps(tick()))
