# ZptMaster — Trading Operation Report

**Generated:** $(date -u)
**Account:** VantageMarkets-Demo (tradeMode=0, DEMO) — NO live capital at risk
**Balance:** $100,425.41 · flat, no open positions

## What is running (all self-healing, all committed)

| Service | Cadence | Purpose |
|---|---|---|
| `trade_loop.sh` | every 15 min | feed → signal → risk gates → bridge → verify fill |
| `news_loop.sh` | every 30 min | headline scan, event-risk pause flag |
| `report_loop.sh` | 00:50 UTC daily | settlement report vs high-water (07:50 GMT+7) |
| `dashboard_loop.sh` | watchdog / 5 min | keeps the audit dashboard alive |
| crontab | mirrors all 4 | belt-and-braces if a loop dies |

## Risk gates (enforced in code, before every order)
- **1% equity max risk per trade** — size derived from real stop distance ×
  per-symbol contract value (correct for USD-, JPY-quoted pairs and gold)
- max **3** concurrent positions · max **6** trades/day
- **−3% daily loss cap** → stop for the day
- **3 consecutive losses → 24h cooldown**
- **mandatory SL + TP on every order** (RR 1.5)
- **news gate**: no new entries within event-risk window (45-min TTL)

## Honest strategy assessment (this is the important part)
I backtested the strategy on real cached history (12k×1h/2y, 2.6k×1d/10y, 10 symbols),
with a 70/30 walk-forward train/test split, across 12 strategy families and
12 parameter combos each.

**Result: no configuration showed a robust, durable edge out-of-sample.**
Trend-following (EMA/Donchian/ADX) was ~break-even to negative; mean-reversion
slightly better on ranges but not net-positive after costs. The best OOS cells
had avgR ≈ +0.1 on tiny samples — not statistically meaningful.

**Conclusion:** I will NOT scale size or claim profit on a non-existent edge.
The engine stays on DEMO with minimum size until genuine positive expectancy is
demonstrated over a meaningful sample. That is the honest, capital-preserving call.

## Optimizer output (latest)
```
$OPT
```

## Files
feed.py · indicators.py · specs.py · strategy.py · strategy2.py · risk.py
engine.py · backtest.py · backtest2.py · optimize2.py · journal.py · news.py
report.py · dashboard.py · *.sh loops · logs/*

## Conway Intelligence API (new, sellable)
A small x402-gated service that sells **computed** FX intelligence (not raw news):
`GET /intel?symbol=EURUSD&tf=1h` → trend, regime/ADX, volatility state + percentile,
key support/resistance, event-risk flag, plain-language actionable summary.
- Price: 0.02 USDC/call (configurable). Payment rail: x402 / USDC on Base.
- Runs open while `X402_PAY_TO` is unset (so the creator can audit freely);
  set `X402_PAY_TO` to monetize. Payment proofs are logged for reconciliation.
- Watchdog + @reboot cron keep it alive. Endpoint 8091 exposed.
