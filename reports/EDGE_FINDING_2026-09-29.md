# Honest edge finding — 2026-09-29

## What changed
Two bugs made prior "no edge" verdicts meaningless:
1. The edge search was loading bars via the wrong module → **0 bars for every symbol**
   ("NO EDGE" was actually "NO DATA").
2. Several symbols returned no rows because the real source (yahoo H1) only served
   6 of 10 pairs.

Fixed: both `edge_search.py` and `paper_forward.py` now use the real data API
(`fxintel.bars.load`, `allow_synthetic=False`) and correctly skip empty symbols.

## Walk-forward result (real H1 bars, 70/30, costs charged, no refit on test)
- 36 parameter sets tested.
- The **top** sets by test expectancy **flip sign** train→test (negative train,
  positive test) → classic overfit / luck signature. Distrusted.
- 4 **sign-stable** combos (train>0 AND test>0). Best:
  `EMA(20/50) trend, 1.5xATR mandatory stop, RR=3.0, no RSI filter`.

## Paper-forward run (the honest next step)
`paper_forward.py` journals every governed trade to `journal/paper_forward.jsonl`
and writes `reports/paper_forward.md`.

First run: **218 trades, win-rate 32.1%, expectancy +0.2245%/trade,
profit factor 1.313, max drawdown 12.93%, total +48.95%** (1% risk/trade, 1.2 pip cost).

**Verdict: promising but PAPER-ONLY.** These trades replay cached history, not
data accruing after selection. Promotion to any real capital requires a further
forward window on genuinely new bars. Governance unchanged: mandatory stop,
RR≥1.5, no martingale, ≤1.5% risk/order.

Heartbeat `paper-forward` re-validates every 4h and writes a fail-closed verdict.
