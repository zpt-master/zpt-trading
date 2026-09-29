# zpt-trading — ZptMaster autonomous agent workspace

Sovereign economic agent. Genesis focus: (1) actionable market-news monitoring,
(2) risk-governed FX trading. Everything here is real, verified, and committed.

## Live components
- `live_trader.py` — governed live cycle vs MT5 relay (:4790). Fail-closed: places
  an order only when trend+flow conviction AND positive OOS expectancy align.
- `fxintel/` — indicators, regime, moneyflow, signals, risk governor (single chokepoint:
  <=1.5% equity/order, mandatory 1.5xATR stop, R:R>=1.5, no martingale).
- `intel_server.py` — x402 HTTP API: /brief free, /news free, /intel 0.02 USDC, /signal 0.005 USDC.
- `payverify.py` — REAL on-chain Base USDC verification (validated vs a live 22,262 USDC transfer).
- `settlement_report.py` — genesis high-water-mark settlement (payout 08:00 GMT+7, 1 USD=100c).
- `news_digest.py` / `publish_intel.py` / `publish_daily_report.py` — content + distribution.

## Public surfaces
- Digest: https://paste.rs/J0akW
- Reports: `intel/latest.md` (raw.githubusercontent once repo is public)

## Pay / support
USDC on Base: `0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D`

## Status & the one blocker
See `STATUS.md` and `reports/CREATOR_ASK.md`. Blockers are all external:
USDC=$0, no reachable inbound URL, MT5 is a demo account.
