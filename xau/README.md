# XAUUSD M5+ Scalping EA — bounty a5e51254

## Deliverables
- `ea/XAUUSD_ScalpM5.mq5` — MT5 Expert Advisor (compile in MetaEditor, attach to XAUUSD M5).
- `xau_scalp.py` — Python backtest of the same rule set with identical risk gates.
- `reports/xau_backtest.json` / `.md` — PnL by day/week/month + gate audit.

## Strategy
EMA(20/50) trend filter + RSI(14) pullback reset entry. Mandatory ATR(14)x1.2 stop,
TP = 2.0R, fixed-fractional risk (0.6%/trade), **no martingale**.

## Risk gates (hard, enforced in EA and backtest)
| Gate | Rule |
|------|------|
| Daily loss | stop trading for the day if equity ≤ −3% |
| Weekly loss | stop trading for the week if equity ≤ −5% |
| Monthly target | ≥ +10% measured (goal, not forced) |
| Per trade | 0.6% risk, mandatory stop, 2R target |

## Data
Real bars only (cache / free feed). Window and source are printed in the report.
