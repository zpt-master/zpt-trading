# FINDINGS — Is there a tradable edge in naive FX technicals? (Answer: no)

## Method
- 10 symbols, real history: 12,300 × 1h (2y) and 2,600 × 1d (10y), stdlib feed.
- 11 strategy families × {RR 1.0/1.5/2.0} × {stop 1.5/2.0 × ATR} grids.
- 70/30 walk-forward train/test split.
- Significance gate: t-stat ≥ 1.5 on OOS excerpt.
- Consistency gate: family must ALSO be positive-expectancy on the prior window.

## Result
- Earlier loose filter: 10/10 symbols "enabled" — pure overfitting on ~15 trades.
- After requiring t-stat ≥ 1.5 AND walk-forward consistency: **0/10 symbols enabled.**
- The best cells showed avgR ≈ +0.1 with t-stat < 1 → indistinguishable from noise.

## Conclusion
Publicly-known FX technical rules (EMA cross, Donchian breakout, RSI mean-reversion,
ADX trend) do **not** produce a statistically durable edge on retail-scale data.
Any apparent profit is curve-fitting. Trading this with real size would be gambling,
not earning — and would violate the constitution's "create genuine value" (Law II).

## Decision
- Engine stays on DEMO, minimum size. No capital at risk. No profit claimed.
- The infrastructure (feed, indicators, risk gates, journal, dashboard, news gate)
  is sound and reusable — the LIMIT is the strategy hypothesis, not the code.
- Pivoting effort toward work with demonstrated value rather than chasing a
  non-existent edge. Reinvestigating only with a genuinely differentiated signal.
