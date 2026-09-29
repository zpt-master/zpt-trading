#!/usr/bin/env python3
"""Nukida trading-discipline rules, encoded from https://nukida.co/ (research/nukida/).

Genesis instructs: "Học hỏi chiến lược giao dịch của Nukida để phục vụ kiếm tiền
bằng trading." Nukida teaches process/psychology discipline, not a magic indicator.
The five extracted principles, made ENFORCEABLE so the live trader obeys them:

  P1  AQ > IQ/EQ — endurance/consistency beats cleverness. Do not abandon a proven
      method after a normal losing streak.
  P2  Fear of entering comes from INCONSISTENCY. Any finite method has a *definite*
      max stop-loss streak. Compute it; expect it; do not method-hop.
  P3  Method quality drives psychology. Rate the method (win-rate band) honestly.
  P4  "Buy and do nothing" — simple + patient. Prefer fewer, higher-conviction trades.
  P5  Treat trading as a PROFESSION, not a game — batch, journal, review.

This module is a pure policy layer: it reads the governed plans/journal and returns
ALLOW / REDUCE / COOLDOWN / BLOCK with a reason. No side effects, no orders.
"""
from __future__ import annotations
import json, math, os
from dataclasses import dataclass, asdict
from typing import List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))

# --- P5: profession-grade operating limits (deliberately strict) --------------
MAX_TRADES_PER_DAY = 3          # P4: fewer, higher-conviction (anti-overtrading)
MAX_CONSECUTIVE_LOSSES = 5      # P2: normal for a healthy finite method; beyond = pause
COOLDOWN_AFTER_LOSS_STREAK = 1  # days to stand aside after hitting the streak cap
MIN_RR = 1.5                    # keep governor's floor, restate here for review


def expected_max_losing_streak(win_rate: float, n_trades: int = 100) -> int:
    """P2: the *definite* max stop-loss streak to EXPECT from a method.

    For independent trades: expected longest run of losses over n trades
    ~= log_{1/p}(n) approximation, floored. Knowing this number is what stops
    you from method-hopping on a normal streak.
    """
    p = max(min(win_rate, 0.999), 1e-6)   # loss prob = 1-win_rate
    q = 1.0 - p
    if q <= 0:
        return 0
    try:
        return max(1, int(math.floor(math.log(n_trades * q + 1) / math.log(1.0 / q)))) if q < 1 else 0
    except (ValueError, ZeroDivisionError):
        return MAX_CONSECUTIVE_LOSSES


def rate_method(win_rate: float) -> str:
    """P3: honest method quality band."""
    if win_rate >= 0.55: return "high"
    if win_rate >= 0.45: return "medium"
    return "low"


@dataclass
class Verdict:
    action: str            # ALLOW | REDUCE | COOLDOWN | BLOCK
    size_mult: float       # 0.0 blocked, else <=1.0
    reasons: List[str]

    def to_dict(self): return asdict(self)


def _journal() -> List[dict]:
    """Read closed-trade rows from the journal (best-effort, schema-tolerant)."""
    rows = []
    for name in ("journal/trades.jsonl", "journal/plans.jsonl"):
        p = os.path.join(HERE, name)
        if not os.path.exists(p):
            continue
        for line in open(p):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if "result" in r or "pnl" in r or "closed" in r:
                rows.append(r)
    return rows


def recent_stats(rows: List[dict], lookback: int = 50) -> dict:
    r = rows[-lookback:]
    closed = [x for x in r if x.get("result") in ("win", "loss") or "pnl" in x]
    wins = [x for x in closed if x.get("result") == "win" or (isinstance(x.get("pnl"), (int, float)) and x["pnl"] > 0)]
    losses = [x for x in closed if x.get("result") == "loss" or (isinstance(x.get("pnl"), (int, float)) and x["pnl"] < 0)]
    # trailing consecutive losses
    streak = 0
    for x in reversed(closed):
        is_loss = x.get("result") == "loss" or (isinstance(x.get("pnl"), (int, float)) and x["pnl"] < 0)
        if is_loss:
            streak += 1
        else:
            break
    wr = (len(wins) / len(closed)) if closed else 0.5
    return {"n": len(closed), "wins": len(wins), "losses": len(losses),
            "win_rate": wr, "loss_streak": streak}


def trades_today() -> int:
    """Count today's entries from the journal (schema-tolerant)."""
    import datetime
    day = datetime.date.today().isoformat()
    n = 0
    for name in ("journal/trades.jsonl", "journal/plans.jsonl"):
        p = os.path.join(HERE, name)
        if not os.path.exists(p):
            continue
        for line in open(p):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if str(r.get("ts", r.get("time", "")))[:10] == day and (r.get("valid") is True or r.get("entered")):
                n += 1
    return n


def evaluate(win_rate: Optional[float] = None) -> Verdict:
    """Return the discipline verdict for the NEXT entry. Pure function of state."""
    rows = _journal()
    st = recent_stats(rows)
    wr = win_rate if win_rate is not None else st["win_rate"]
    reasons: List[str] = []
    action, mult = "ALLOW", 1.0

    # P1/P2: respect the expected streak; do not method-hop, but DO pause past the band.
    exp_streak = expected_max_losing_streak(wr)
    if st["loss_streak"] >= MAX_CONSECUTIVE_LOSSES:
        action, mult = "COOLDOWN", 0.0
        reasons.append(f"P2 loss_streak={st['loss_streak']} >= cap {MAX_CONSECUTIVE_LOSSES} "
                       f"(expected max ~{exp_streak}); stand aside {COOLDOWN_AFTER_LOSS_STREAK}d, do NOT switch method")
    elif st["loss_streak"] >= max(2, exp_streak - 1):
        action, mult = "REDUCE", 0.5
        reasons.append(f"P2 near expected streak (got {st['loss_streak']}, expected ~{exp_streak}); halve size")

    # P4/P5: anti-overtrading
    tdy = trades_today()
    if tdy >= MAX_TRADES_PER_DAY:
        action, mult = "BLOCK", 0.0
        reasons.append(f"P4/P5 trades_today={tdy} >= cap {MAX_TRADES_PER_DAY}; patience over volume")

    # P3: method rating for the record
    reasons.append(f"P3 method quality: {rate_method(wr)} (win_rate={wr:.2f}, n={st['n']})")
    if action == "ALLOW":
        reasons.append("P1 consistency: method within expected variance -> keep executing unchanged")

    return Verdict(action, round(mult, 3), reasons)


def main():
    v = evaluate()
    print(json.dumps(v.to_dict(), indent=2))
    rows = _journal()
    st = recent_stats(rows)
    print("stats:", json.dumps(st), "| trades_today:", trades_today(),
          "| expected_max_streak ~", expected_max_losing_streak(st["win_rate"]))


if __name__ == "__main__":
    main()
