#!/usr/bin/env python3
"""Report the internal-ledger MT5 settlement status (08:00 GMT+7 payout).

Reads the creator's cost-meter ledger (:4790 /mt5/state -> settlement), which
implements the genesis high-water-mark rule: every day at 08:00 GMT+7 (01:00 UTC)
the increase in peak balance over the existing mark is credited to the internal
balance; a day that does not exceed the mark counts as no-profit (loss).
Trading account currency : internal cents = 1 USD : 100 cents (1:1 USD).
"""
import json, os, urllib.request
from datetime import datetime, timezone, timedelta

BASE = os.environ.get("LEDGER_URL", "http://127.0.0.1:4790")
TOKEN = os.environ.get("LEDGER_TOKEN", "change-me-shared-secret")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "settlement.md")

GMT7 = timezone(timedelta(hours=7))


def get(path):
    r = urllib.request.Request(BASE + path, method="GET")
    r.add_header("X-Auth-Token", TOKEN); r.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(r, timeout=10) as resp:
        return json.loads(resp.read().decode())


def main():
    st = get("/mt5/state")
    s = st.get("settlement") or {}
    snap = st.get("snapshot") or {}
    bal_cents = get("/balance")
    hwm = s.get("hwm"); peak = s.get("periodPeak")
    nxt = s.get("nextSettlementTs")
    def fmt(ms):
        if not ms: return "-"
        return datetime.fromtimestamp(ms/1000, GMT7).strftime("%Y-%m-%d %H:%M GMT+7")
    lines = ["# MT5 → Internal settlement (high-water-mark)", "",
             f"Generated: {datetime.now(GMT7).isoformat()}", "",
             f"- Trading balance: **{snap.get('balance')} {snap.get('currency','USD')}**",
             f"- Equity: {snap.get('equity')}",
             f"- High-water mark (mt5_hwm): **{hwm}**",
             f"- Period peak: {peak}",
             f"- Next payout: **{fmt(nxt)}**",
             f"- Settlement enabled: {s.get('enabled')} @ hour {s.get('settlementHourUtc')} UTC (08:00 GMT+7)",
             f"- Internal balance: {bal_cents.get('balanceCents')} cents (tier {bal_cents.get('tier')})",
             "",
             "Rule: at 08:00 GMT+7 the rise of the period peak above the mark is credited",
             "(1 USD = 100 cents = 1:1). If peak <= mark, the day counts as a loss and the",
             "mark is NOT lowered (drawdown high-water mark) — per genesis.",
             ]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
