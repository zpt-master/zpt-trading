#!/usr/bin/env python3
"""Emit a daily Nukida-discipline review to reports/discipline.md.
Part of the 'profession not a game' (P5) commitment: journal + review every day."""
import datetime, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nukida_discipline as nk

def main():
    HERE = os.path.dirname(os.path.abspath(__file__))
    st = nk.recent_stats(nk._journal())
    v = nk.evaluate()
    exp = nk.expected_max_losing_streak(st["win_rate"])
    day = datetime.date.today().isoformat()
    md = f"""# Discipline Review — {day}

Method quality (P3): **{nk.rate_method(st['win_rate'])}** (win_rate={st['win_rate']:.2f}, n={st['n']})
Expected max losing streak (P2): **~{exp}** — anticipated, not a reason to switch method
Current loss streak: {st['loss_streak']} · trades today: {nk.trades_today()}/{nk.MAX_TRADES_PER_DAY}

## Next-entry verdict: **{v.action}** (size x{v.size_mult})
""" + "\n".join(f"- {r}" for r in v.reasons) + """

---
Principles (nukida.co): P1 AQ>IQ (consistency) · P2 fear comes from inconsistency —
know the expected streak · P3 rate the method honestly · P4 simple + patient, fewer
higher-conviction trades · P5 treat it as a profession — journal and review.
"""
    with open(os.path.join(HERE, "reports", "discipline.md"), "w") as f:
        f.write(md)
    print(md)

if __name__ == "__main__":
    main()
