"""One trading cycle: feed -> strategy -> risk gate -> bridge order.
Usage:  python3 engine.py DRY_RUN   (analyse + log, place nothing)
        python3 engine.py LIVE      (place order if all gates pass)
"""
import sys, json, os, time, urllib.request
from datetime import datetime, timezone
import feed, strategy, risk

BRIDGE = "http://localhost:4790"
TOKEN  = os.environ.get("MT5_TOKEN", "change-me-shared-secret")
LOG    = os.path.join(os.path.dirname(__file__), "logs", "engine.log")
WATCH  = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD"]

def log(msg):
    line = f"{datetime.now(timezone.utc).isoformat()} {msg}"
    print(line)
    with open(LOG, "a") as f: f.write(line + "\n")

def bridge(path, method="GET", body=None):
    req = urllib.request.Request(BRIDGE + path, method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body else None)
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.load(r)

def main():
    live = len(sys.argv) > 1 and sys.argv[1].upper() == "LIVE"
    st = bridge("/mt5/state")
    snap = st["snapshot"]
    equity, balance = snap["equity"], snap["balance"]
    open_n = len(snap.get("positions") or [])
    mode = "DEMO" if snap.get("tradeMode") == 0 else "LIVE"
    log(f"--- cycle start mode={mode} bal={balance:.2f} eq={equity:.2f} open={open_n} live={live}")

    s = risk.load()
    s = risk.check_day(s, balance)

    if open_n > 0:
        # report each open position's unrealized P&L for the daily ledger
        for p in snap["positions"]:
            log(f"  position {p.get('symbol')} {p.get('type')} vol={p.get('volume')} "
                f"profit={p.get('profit')} price={p.get('priceOpen')}->{p.get('priceCurrent')}")
        risk.save(s)
        log("cycle end: positions open, no new entries")
        return

    ok, why = risk.can_open(s, equity, open_n)
    if not ok:
        log(f"risk gate closed: {why}"); risk.save(s); return

    for sym in WATCH:
        try:
            cs = feed.candles(sym, interval="1h", rng="10d")
        except Exception as e:
            log(f"  {sym}: feed error {e}"); continue
        sig = strategy.signal(cs)
        if not sig:
            log(f"  {sym}: no signal (last={cs[-1]['c']})"); continue

        sl, tp = strategy.levels(sig["side"], sig["price"], sig["sl_dist"])
        # JPY pairs have 0.01 pip
        pip = 0.01 if sym.endswith("JPY") else 0.0001
        vol = risk.position_size(equity, sig["sl_dist"], pip=pip)
        log(f"  {sym}: SIGNAL {sig['side']} @ {sig['price']:.5f} sl={sl:.5f} tp={tp:.5f} "
            f"vol={vol} ({sig['reason']})")
        if live and vol > 0:
            try:
                r = bridge("/mt5/order", "POST", {
                    "symbol": sym + "+", "side": sig["side"], "volume": vol,
                    "sl": round(sl, 5), "tp": round(tp, 5),
                    "comment": f"zpt {sig['side']} ema"})
                log(f"  -> order submitted: {r}")
                s["trades_today"] += 1
            except Exception as e:
                log(f"  -> order FAILED: {e}")
        elif vol <= 0:
            log("  -> skipped: computed volume 0 (stop too wide for equity)")
    risk.save(s)
    log("--- cycle end")

if __name__ == "__main__":
    main()
