#!/usr/bin/env python3
"""fxintel/settlement.py - High-Water-Mark daily settlement per genesis spec.

Rules (from creator's genesis prompt):
  * Interest is paid at 08:00 GMT+7 each day.
  * "Capital" = the MT5 balance AFTER the prior interest payout.
  * If a day is a loss, the highest balance reached becomes the new benchmark:
    you are only paid interest on NEW HIGHS above that HWM.
  * Conversion: 1 USD MT5 = 1 USD operating fee (1:1).

So: payable = max(0, balance_now - HWM_after_last_payout).
HWM never decreases. A losing day does NOT create a payout; it just leaves the
HWM where it was (the peak), so recovery must first re-cross the old peak.
Stdlib-only, deterministic, unit-tested.
"""
import json, os, datetime as dt

TZ_OFFSET = 7  # GMT+7


def payout(balance: float, hwm: float, rate: float = 0.0) -> dict:
    """Compute today's settlement. rate>0 pays interest on the new-high excess."""
    balance = float(balance); hwm = float(hwm)
    excess = max(0.0, balance - hwm)
    interest = round(excess * float(rate), 2)
    new_hwm = max(hwm, balance)
    return {
        "balance": round(balance, 2),
        "hwm": round(hwm, 2),
        "excess_above_hwm": round(excess, 2),
        "rate": rate,
        "interest_due_usd": interest,
        "new_hwm": round(new_hwm, 2),
        "is_new_high": balance > hwm,
        "payout_due": balance > hwm,
    }


def settle_day(state: dict, balance: float, rate: float = 0.0, when=None) -> dict:
    """Apply one day's settlement to persistent state (mutates a copy)."""
    r = payout(balance, state.get("hwm", 0.0), rate)
    when = when or dt.datetime.now(dt.timezone.utc)
    r["credited_at"] = (when + dt.timedelta(hours=TZ_OFFSET)).strftime("%Y-%m-%d 08:00 GMT+7")
    state = dict(state); state["hwm"] = r["new_hwm"]
    state["last_settlement"] = r
    state.setdefault("ledger", []).append(r)
    state["ledger"] = state["ledger"][-365:]
    # 1:1 conversion note
    r["operating_credit_usd"] = r["interest_due_usd"]
    return state


def next_run_utc(now=None):
    """Next 08:00 GMT+7 boundary as UTC ISO."""
    now = now or dt.datetime.now(dt.timezone.utc)
    local = now + dt.timedelta(hours=TZ_OFFSET)
    target = local.replace(hour=8, minute=0, second=0, microsecond=0)
    if target <= local:
        target += dt.timedelta(days=1)
    return (target - dt.timedelta(hours=TZ_OFFSET)).isoformat()


if __name__ == "__main__":
    st = {"hwm": 100000.0}
    for bal, note in [(100425.41, "up day"), (100100.00, "down day"), (100900.00, "recovery"),
                      (100500.00, "below peak"), (101500.00, "new high")]:
        st = settle_day(st, bal)
        s = st["last_settlement"]
        print(f"{note:12s} bal={bal:>10.2f} hwm={s['hwm']:>10.2f} "
              f"interest=${s['interest_due_usd']:>8.2f} newHWM={s['new_hwm']:>10.2f}")
    print("next payout (UTC):", next_run_utc())
