# ZptMaster — Risk-Governed Market Intelligence (x402 API)

Autonomous agent selling **actionable, risk-governed** FX/macro intelligence.
No signal spam. No martingale. Capital preservation first.

## Buy intelligence (pay-per-call, USDC on Base)
| Endpoint | Price | What you get |
|---|---|---|
| `GET /intel?symbol=EURUSD` | **0.02 USDC** | Trend, regime, money-flow, vol, and a rule-bound trade plan |
| `GET /signal?symbol=EURUSD` | 0.005 USDC | Just the governed plan (entry/stop/target/size/R) |
| `GET /brief` | **free** | Daily brief: actionable headlines + governed plans |
| `GET /news` | free | Curated actionable headlines |
| `GET /.well-known/x402` | free | x402 discovery manifest |

**Payment**: x402 — send USDC on Base (eip155:8453) to
`0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D`, pass the tx hash in `X-PAYMENT`.
Verification is **real on-chain** (receipt status + USDC Transfer log to payTo,
≥ required units, fail-closed). See `tests/test_payverify_live.py`.

## Why it's different
Every plan enforces: **≤1% equity risk**, mandatory 1.5×ATR stop, target ≥1.5R,
no averaging/martingale, hard size cap. When no symbol has aligned trend + money-flow
conviction, the engine **stands aside** — "no trade is better than a bad trade."
Principles sourced from Nukida (psychology & capital preservation) —
see `knowledge/nukida_lessons.md`.

## Track record
Honest and public: `reports/track_record.md` (paper-traded, updated hourly).
An empty record is a *feature* — it means the rules found no edge and preserved capital.

## Run
```
python3 intel_service.py      # :8091, serves storefront + x402 endpoints
python3 paper_trader.py       # hourly -> reports/track_record.md
python3 daily_brief.py        # daily  -> reports/daily_brief.md
```

## Wallet
`0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D` (USDC on Base)
