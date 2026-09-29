#!/usr/bin/env python3
"""settle_daily.py - genesis daily settlement (interest 08:00 GMT+7, HWM rule).

Rules (from genesis):
  * capital = MT5 balance after interest is paid
  * if a day loses, the HIGHEST balance becomes the HWM; a later day that ends
    below that HWM counts as a LOSS no matter how much it "made" intraday
  * 1 USD = 100 cents conversion between MT5 money and operating fees

Reads state/hwm.json (HWM + capital) and the broker state (if the EA is live),
computes the payout, appends an auditable line to reports/settlement.md, and
persists the new HWM. Fail-soft: with no broker it reports the paper HWM only.
"""
from __future__ import annotations
import os, json, datetime as dt

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
os.makedirs("state", exist_ok=True)
HWM_F = "state/hwm.json"
OUT = "reports/settlement.md"
USD_CENTS = 100
DEFAULT_HWM = 100425.41   # live demo equity baseline (acct 25947886)


def load_hwm() -> dict:
    try:
        d = json.load(open(HWM_F))
        d.setdefault("hwm", DEFAULT_HWM)
        d.setdefault("capital", d["hwm"])
        return d
    except Exception:
        return {"hwm": DEFAULT_HWM, "capital": DEFAULT_HWM}


def save_hwm(d: dict):
    json.dump(d, open(HWM_F, "w"), indent=2)


def broker_equity():
    try:
        import mt5_bridge_file as B
        st = B.read_state()
        eq = st.get("equity")
        return float(eq) if eq else None
    except Exception:
        return None


def settle(day=None):
    day = day or dt.datetime.utcnow().strftime("%Y-%m-%d")
    d = load_hwm()
    hwm, capital = float(d["hwm"]), float(d.get("capital", d["hwm"]))
    eq = broker_equity()
    source = "broker(MT5)" if eq is not None else "paper(no broker)"
    equity = eq if eq is not None else capital
    profit = equity - hwm
    new_hwm = max(hwm, equity)
    payout_cents = int(round(max(0.0, profit) * USD_CENTS))
    status = "PROFIT" if profit > 0 else ("FLAT" if profit == 0 else "LOSS(below HWM)")
    rec = {"day": day, "hwm_before": round(hwm, 2), "equity": round(equity, 2),
           "profit_units": round(profit, 2), "payout_cents": payout_cents,
           "hwm_after": round(new_hwm, 2), "status": status, "source": source}
    d["hwm"] = new_hwm
    d["capital"] = equity
    save_hwm(d)
    line = (f"| {day} | {rec['hwm_before']:.2f} | {rec['equity']:.2f} | "
            f"{rec['profit_units']:+.2f} | {payout_cents} | {status} | {source} |\n")
    new = not os.path.exists(OUT)
    with open(OUT, "a") as f:
        if new:
            f.write("# ZptMaster Daily Settlement (HWM rule)\n\n"
                    "Interest is evaluated at 08:00 GMT+7. The high-water mark only "
                    "rises; a day ending below it counts as a LOSS regardless of "
                    "intraday gains. 1 USD = 100 cents.\n\n"
                    "| day | HWM before | equity | profit | payout(cents) | status | source |\n"
                    "|---|---|---|---|---|---|---|\n")
        f.write(line)
    print(json.dumps(rec))
    return rec


if __name__ == "__main__":
    settle()
