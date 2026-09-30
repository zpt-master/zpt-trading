# XAUUSD M5 Scalp — Definitive Verdict (bounty a5e51254 methodology)

## Data (real, this time)
- Source: **Binance PAXGUSDT** (PAXG is 1:1 gold-backed ≈ XAUUSD spot), `fxintel/binance_gold.py`.
- **210,384 real M5 bars, 2024-09-29 → 2026-09-29 (exactly 2 years).**
- This satisfies the bounty's "M5 và trên (M5 and above), 2 years" requirement.

## Full-window single-config run (EA defaults)
| Metric | Value |
|---|---|
| Trades | 15,169 |
| Win rate | 33.1% |
| Total return | **−50.7%** |
| Max drawdown | 51.6% |
| Profit factor | 0.882 |
Daily gate (−3%) OK, weekly gate (−5%) OK; ≥5 trades/wk OK (143/wk); 10%/month target NOT met.

## 144-config sweep + walk-forward (no lookahead)
- Train on year 1 (2024-09→2025-09): **every one of 144 configs lost money** (best was −12.8%).
- Best-in-sample config tested on year 2 (2025-09→2026-09): **−62.0%**, max DD 84.9%.
- `reports/xau_sweep.json`, runner `xau/sweep_pure.py` (pure Python, no deps).

## Conclusion
The EMA/RSI/ATR scalp rule set is **loss-making and unstable** across parameters and time.
**Do not deploy.** This is the disciplined, capital-preserving outcome — consistent with the
independent bootstrap/permutation finding (`edge_significance.py`: edge not proven).
The EA and risk gates are correct engineering; the *alpha* is absent.

## 2026-09-30 — eval_harness.py (multi-symbol walk-forward gate)

Added a reusable OOS gate (`eval_harness.py`) so no rule reaches capital without
clearing an honest out-of-sample test on real bars.

Run across 6 symbols × 3 built-in rules (momentum / meanrev / breakout) =
18 tests. Exactly ONE passed (USDCAD momentum: n=180, exp=+0.322R, t=+3.53).

That hit rate is exactly what multiple-testing noise produces (~5% false
discovery at t>=2). Per-symbol cherry-picking would be self-deception.

**Verdict: EDGE NOT PROVEN. Stand aside. No capital risked.**

Rule going forward: a candidate must clear the gate on ALL symbols (not one),
or be validated with a genuine multiple-testing correction, before live_trader
is permitted to size it.
