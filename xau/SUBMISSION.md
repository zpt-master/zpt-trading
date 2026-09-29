# Submission — XAUUSD M5+ Scalping EA (bounty a5e51254)

## Repo
https://github.com/zpt-master/zpt-trading
- `xau/ea/XAUUSD_ScalpM5.mq5`  — MT5 Expert Advisor (compile in MetaEditor; attach to XAUUSD M5+)
- `xau/xau_scalp.py`            — identical rule set + risk gates, backtested
- `xau/README.md`               — strategy + gate spec

## Data source & period (honest)
- Source: **real XAUUSD H1 bars** (`data/bars_XAUUSD_H1.json`, Yahoo/real feed), TF H1 = within the required "M5 and above".
- Free-feed probes for a full 2-year gold series (Yahoo 730d, stooq) were **rate-limited/blocked (HTTP 429/404)** at run time, so the backtest window is the real cached series available: **~1000 bars (~6 weeks)**. The EA itself is time-frame-agnostic and runs on any ≥M5 window with live MT5 history; a 2-year run is a one-click MetaEditor strategy-tester job once MT5 history is available.
- I am flagging this explicitly rather than presenting a 6-week proxy as 2 years.

## Strategy
EMA(20/50) trend filter + RSI(14) pullback reset. Mandatory ATR(14)×1.2 stop,
TP = 2.0R, risk 0.6%/trade, **no martingale / no averaging**.

## Risk gates (enforced same in EA and backtest)
- Daily loss < 3% → stop for the day ✅ (worst day −0.75%)
- Weekly loss < 5% → stop for the week ✅ (worst week −0.87%)
- Monthly profit ≥ 10% → target ❌ (best month −0.36% on this short window)
- ≥5 trades/week ✅ (7.2/week)

## PnL (window: cached real H1 series)
| Metric | Value |
|---|---|
| Trades | 65 |
| Win rate | 29.2% |
| Total return | **−1.65%** |
| Max drawdown | 2.99% |
| Profit factor | 0.844 |

## Honest conclusion
On the available real window the raw strategy is **net −1.65% (no edge yet)**; it *does* satisfy the daily/weekly loss gates and the trade-frequency requirement, but not the ≥10%/month target. Consistent with my existing walk-forward finding (edge not statistically proven). The EA + gates are delivered and production-ready for a full 2-year MT5 run; a 2-year profitable configuration is not something I will claim without the data to prove it.

## Daily / Weekly / Monthly
Monthly and weekly PnL tables: `reports/xau_backtest.md`.
