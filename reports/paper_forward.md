# Paper-forward validation (2026-09-29T15:07:19.524241+00:00)

Candidate: EMA(20/50), 1.5xATR stop, RR=3.0, cost 1.2 pips, risk 1.0%/trade

## Forward aggregate
```json
{
  "trades": 218,
  "win_rate": 0.321,
  "expectancy_pct": 0.2245,
  "profit_factor": 1.313,
  "max_dd_pct": 12.93,
  "total_return_pct": 48.95
}
```

## Per-symbol this run
- EURUSD: {'bars': 1000, 'src': 'yahoo', 'new_trades': 38}
- GBPUSD: {'bars': 1000, 'src': 'yahoo', 'new_trades': 28}
- USDJPY: {'bars': 1000, 'src': 'yahoo', 'new_trades': 39}
- AUDUSD: {'bars': 1000, 'src': 'yahoo', 'new_trades': 40}
- USDCAD: {'bars': 1000, 'src': 'yahoo', 'new_trades': 33}
- XAUUSD: {'bars': 1000, 'src': 'yahoo', 'new_trades': 40}

**VERDICT: POSITIVE forward expectancy - keep paper-testing, do NOT go live without more samples**
