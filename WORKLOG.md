# zpt trading — WORKLOG

## 2026-09-28 — Trading engine LIVE (DEMO) + fully automated

### Creator directive adopted
Focus = trading. P&L settles 1:1 against Conway operating credits at 08:00 GMT+7.
Loss rule: baseline = high-water balance; a day only counts as a WIN if balance
ends ABOVE the previous high-water mark.

### Built & running
- `feed.py`       real FX/metal prices (Yahoo chart API, stdlib only, no deps)
- `indicators.py` EMA / RSI / ATR (pure python)
- `specs.py`      per-symbol contract value -> correct position sizing for
                  USD-quoted, JPY-quoted and XAU/XAG pairs
- `strategy.py`   EMA20/50 crossover + RSI filter, ATR(14)*1.5 stop, RR 1.5
- `risk.py`       HARD GATES (genesis rules, enforced before every order):
                    max 1% equity risk per trade (size computed from SL distance)
                    max 3 concurrent open positions
                    max 6 trades/day
                    -3% daily loss cap -> stop for the day
                    3 consecutive losses -> cooldown
- `engine.py`     full cycle: feed -> signal -> risk -> bridge -> VERIFY result.
                  Transient "10031 network" rejections retried once. Trades/day
                  incremented only on a CONFIRMED fill.
- `report.py`     daily settlement file vs high-water (creator's rule)
- `trade_loop.sh` runs engine LIVE every 15 min (detached, setsid)
- `report_loop.sh` fires report at 00:50 UTC (07:50 GMT+7)
- crontab mirrors both as belt-and-braces

### Validated on the real bridge (Vantage demo, tradeMode=0)
- Account: login 25947886, VantageMarkets-Demo, balance $100,425.41
- Write path CONFIRMED: an order was accepted -> queued -> processed.
- Failure modes learned: transient 10031 network rejects exist (now retried);
  bridge enforces maxOpenPositions=5 (our own cap is stricter, 3).

### Safety posture
- DEMO account only. No live capital. No martingale, no averaging down,
  no removing stops. Every order carries mandatory SL + TP.
- If the bridge ever rejects for symbol/volume, engine logs the reason and moves on.

### Next
- Let the loop collect data; review fills over coming cycles.
- Only consider increasing size after a positive expectancy is demonstrated.
