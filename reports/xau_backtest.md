# XAUUSD M5+ scalp backtest (H1)

Source: cache:data/bars_XAUUSD_H1.json  Period: 2026-07-29 -> 2026-09-29

Strategy: EMA20/50 trend + RSI(14) pullback reset, ATR stop 1.2x, RR 2.0, cost $0.35

## Headline
```json
{
  "trades": 65,
  "win_rate": 0.292,
  "start_eq": 10000.0,
  "final_eq": 9835.47,
  "total_return_pct": -1.65,
  "max_dd_pct": 2.99,
  "avg_R": -0.042,
  "profit_factor": 0.844
}
```

## Gates
```json
{
  "worst_day_usd": -75.43,
  "worst_day_pct": -0.75,
  "day_gate_3pct_ok": true,
  "worst_week_usd": -86.85,
  "worst_week_pct": -0.87,
  "week_gate_5pct_ok": true,
  "best_month_usd": -36.06,
  "best_month_pct": -0.36,
  "month_target_10pct_ok": false,
  "trades_per_week": 7.2,
  "min_5_per_week_ok": true
}
```

## Monthly PnL (USD)
- 2026-08: -36.06
- 2026-09: -128.47

## Weekly PnL (USD)
- 2026-W32: 19.28
- 2026-W33: 27.92
- 2026-W34: -12.37
- 2026-W35: -70.90
- 2026-W36: -20.68
- 2026-W37: -46.19
- 2026-W38: 6.32
- 2026-W39: -86.85
- 2026-W40: 18.93
