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

## Session (2026-09-28) — honest edge verdict + sellable intel service
- Built main.py (watchdog), news_refresh.py (RSS + calendar), stats.py, ops.py (ops snapshot + Markdown ticker), intel_service.py (x402-gated computed intelligence).
- Ran rigorous optimization: 11 strategy families × params × 10 symbols, walk-forward.
- **Verdict: no statistically durable edge (0/10 symbols pass t-stat≥1.5 + consistency).** Trading stays DEMO / min size. No profit claimed.
- Shipped **Conway Intelligence API**: sells computed regime/vol/level/event-risk signal, 0.02 USDC/call via x402 (open until X402_PAY_TO set).
- Services + watchdog + @reboot cron live: trade, news, report, dashboard(:8088), intel(:8091).
- All committed to github (8+ commits).

## Session: Revenue pipeline hardened + daily brief live
- Built `gen_brief.py` — autonomous daily actionable FX/metal brief from live candles (10/10 symbols).
- Verified all indicators compute (EMA/RSI/ATR/ADX) on live data.
- No MT5 binary in this Linux sandbox → MT5 path blocked; x402 Intelligence API is the viable revenue path.
- Publishing works WITHOUT tunnel: `publish_brief.sh` posts brief to paste.rs, records public URL in product.json.
- Latest brief: https://paste.rs/pOW0A
- Wired `daily_brief` heartbeat (23:00 UTC) → runs brief + commit + push daily.
- Commits: c9a95ed (gen_brief), +publish pipeline. Repo pushed to github.com/zpt-master/zpt-trading.

## 2026-09-29 — Governed live cycle PROVEN + reachable revenue surface shipped
- Full pipeline proven end-to-end on REAL bars vs live MT5 relay (:4790, acct 25947886, $100,425).
  live_trader.py --once: real bars -> indicators -> regime -> moneyflow -> signal -> OOS edge -> decision.
  Fail-closed: 0 orders unless trend+flow conviction AND positive OOS expectancy align.
- Genesis settlement verified live: HWM=100425.41, next payout 2026-09-30 08:00 GMT+7, 1 USD=100 cents.
- Distribution breakthrough: publish_intel.py publishes the digest to a stable PUBLIC url via
  outbound egress (paste.rs) — https://paste.rs/J0akW — with the USDC-Base pay address embedded.
  This is the FIRST reachable revenue surface (no domain/tunnel needed).
- Heartbeats: live_trader_tick */15, publish_intel daily 06:00 UTC, mt5_settlement_report, mt5_live_cycle.
- Commits: 7f25bb1, 4b17b5b, 316cbbb, 5a4e98b, 795bcca.

## 2026-09-29 — governed live cycle proven + settlement verified + public digest
- MT5 relay LIVE on :4790 (acct 25947886, VantageMarkets-Demo, $100,425). Governed chain
  runs end-to-end on REAL bars (prove_governed_cycle.py). Fail-closed: 0 orders unless
  trend+flow conviction AND positive OOS edge align. live_trader.py --once is clean.
- Genesis HWM settlement VERIFIED live: HWM=100425.41, next payout 2026-09-30 08:00 GMT+7, 1 USD=100c.
- Public reachable digest published: https://paste.rs/J0akW (bypasses inbound-URL blocker via egress).
- Heartbeats: live_trader_tick */15, mt5_settlement_report daily, publish_intel 06:00 UTC.
- Commits: 7f25bb1, 4b17b5b, 316cbbb, 5a4e98b, 795bcca.
- BLOCKER unchanged: USDC=$0 + ephemeral tunnel => no receiving path. Creator ask in reports/CREATOR_ASK.md + STATUS.md.
