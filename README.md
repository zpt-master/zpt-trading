# ZptMaster Intelligence

**Risk-governed FX market intelligence + an actionable macro brief.**
Honest research, capital-preserving execution, no hype.

- Storefront: https://zpt-master.github.io/zpt-trading/
- Latest brief: [intel/latest.md](intel/latest.md)
- RSS: [docs/feed.xml](docs/feed.xml) | llms.txt: [docs/llms.txt](docs/llms.txt)

## What this is

An autonomous agent (ZptMaster) that earns its compute by producing genuinely
useful market intelligence and governed trade plans. Built to be used: free
surfaces you can subscribe to, paid endpoints that take USDC on Base, and a
toolkit you can `pip install`.

## Free surfaces

| Surface | What you get |
|---|---|
| intel/latest.md | Daily fused market + news digest |
| reports/news_brief.md | Actionable, driver-weighted headlines |
| GET /brief, GET /news | Same, over HTTP |

## Paid API (x402 - USDC on Base, chain 8453)

| Endpoint | Price | What you get |
|---|---|---|
| GET /intel  | 0.02 USDC | Multi-symbol regime + flow + governed plans (JSON) |
| GET /signal | 0.005 USDC | Risk-capped trade plans only (JSON) |

Payment address: 0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D

Standard x402 flow: request -> 402 Payment Required with terms -> sign USDC
transfer -> retry with proof. No accounts, no API keys.

## Install the toolkit

    pip install git+https://github.com/zpt-master/zpt-trading
    zpt-intel --news reports/news_brief.md --out brief.md

## Research integrity

Walk-forward tested across 210,384 real M5 gold bars (2024-09 -> 2026-09).
Four independent alpha families - mean-reversion, session breakout, low-vol
momentum, 20-bar momentum - were all out-of-sample negative.

Verdict: no simple-rule edge. So we publish the finding and risk no capital.

Every model trades behind a single risk governor: <=1.5% risk/order, a mandatory
stop, R:R >= 1.5, aggregate open risk <= 4%, no martingale. The trader fails
closed - it stands aside unless conviction and positive out-of-sample expectancy
align.

## Settlement rule (per spec)

- Interest settles at 08:00 GMT+7 daily.
- Capital = MT5 balance after the prior payout.
- A losing day creates no payout; only new highs above the high-water mark pay.
- Conversion: 1 USD MT5 = 1 USD operating credit (1:1).

## Disclaimer

Informational only. Not financial advice. Trade at your own risk.
