"""One trading cycle: feed -> strategy -> risk -> bridge -> verify.
Order results are polled; transient (10031 network) rejections retry ONCE.
Trades/day is counted only on a confirmed fill."""
import sys, json, os, time, urllib.request
from datetime import datetime, timezone
import feed, strategy, risk

BRIDGE = "http://localhost:4790"
TOKEN  = os.environ.get("MT5_TOKEN", "change-me-shared-secret")
LOG    = os.path.join(os.path.dirname(__file__), "logs", "engine.log")
WATCH  = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD"]
TRANSIENT = ("10031", "network connection", "no connection")

def log(m):
    line = f"{datetime.now(timezone.utc).isoformat()} {m}"
    print(line)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "a").write(line + "\n")

def bridge(path, method="GET", body=None):
    req = urllib.request.Request(BRIDGE + path, method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body else None)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)

def find_order(oid):
    st = bridge("/mt5/state")
    for o in st.get("orders", []):
        if o.get("id") == oid:
            return o
    return None

def submit_and_verify(sym, side, vol, sl, tp):
    """Returns (filled:bool, detail:str)."""
    for attempt in (1, 2):
        try:
            r = bridge("/mt5/order", "POST", {"symbol": sym + "+", "side": side,
                "volume": vol, "sl": round(sl, 5), "tp": round(tp, 5),
                "comment": "zpt auto"})
        except Exception as e:
            log(f"  submit error (attempt {attempt}): {e}"); time.sleep(15); continue
        oid = r.get("id")
        if not oid:
            log(f"  no order id: {r}"); return False, str(r)
        for _ in range(20):                      # poll up to ~60s
            time.sleep(3)
            o = find_order(oid)
            if o and o.get("status") in ("filled", "rejected", "error"):
                if o["status"] == "filled":
                    return True, o.get("result_json", "")
                reason = str(o.get("result_json", ""))
                if any(t in reason for t in TRANSIENT) and attempt == 1:
                    log(f"  transient reject, retrying once: {reason}")
                    time.sleep(10); break
                return False, reason
        else:
            return False, "timeout waiting for result"
    return False, "exhausted retries"

def main():
    live = len(sys.argv) > 1 and sys.argv[1].upper() == "LIVE"
    st = bridge("/mt5/state"); snap = st["snapshot"]
    equity, balance = snap["equity"], snap["balance"]
    pos = snap.get("positions") or []
    mode = "DEMO" if snap.get("tradeMode") == 0 else "LIVE"
    log(f"--- cycle mode={mode} eq={equity:.2f} open={len(pos)} live={live}")

    s = risk.check_day(risk.load(), balance)

    # reconcile truth: if flat but a position closed, that's a settled trade
    if pos:
        for p in pos:
            log(f"  POS {p.get('symbol')} {p.get('type')} v={p.get('volume')} pnl={p.get('profit')}")
        risk.save(s); log("cycle end: in position"); return
    risk.save(s)

    import os as _os
    _flag=os.path.join(os.path.dirname(os.path.abspath(__file__)),"pause_news.flag")
    if _os.path.exists(_flag):
        import json as _j
        log(f"news gate: event risk -> no new entries ({_j.load(open(_flag)).get('reason','')[:70]})")
        return
    ok, why = risk.can_open(s, equity, len(pos))
    if not ok:
        log(f"risk gate closed: {why}"); return

    for sym in WATCH:
        try:
            cs = feed.candles(sym, interval="1h", rng="10d")
        except Exception as e:
            log(f"  {sym}: feed error {e}"); continue
        sig = strategy.signal(cs)
        if not sig:
            continue
        price = sig["price"]
        sl, tp = strategy.levels(sig["side"], price, sig["sl_dist"])
        vol = risk.position_size(equity, sym, sig["sl_dist"], price)
        log(f"  {sym}: {sig['side'].upper()} @{price:.5f} sl={sl:.5f} tp={tp:.5f} vol={vol} ({sig['reason']})")
        if not live:
            log("  DRY: would submit"); continue
        if vol <= 0:
            log("  skip: vol=0"); continue
        filled, detail = submit_and_verify(sym, sig["side"], vol, sl, tp)
        log(f"  -> {'FILLED' if filled else 'REJECTED'}: {detail}")
        if filled:
            s = risk.load(); s["trades_today"] += 1
            s["high_water_balance"] = max(s["high_water_balance"], balance)
            risk.save(s)
            break   # one entry per cycle
    log("--- cycle end")

if __name__ == "__main__":
    main()
