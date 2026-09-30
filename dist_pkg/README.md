# zpt-intel

Risk-governed FX market intelligence. Honest strategy research + actionable news.

## Install
    pip install .

## Use
    zpt-intel --news reports/news_brief.md --market docs/brief.json --out brief.md

## Paid API (x402, USDC on Base)
- `GET /brief`  free — daily markdown brief
- `GET /news`   free — actionable headlines
- `GET /intel`  0.02 USDC — multi-symbol regime + governed plans (JSON)
- `GET /signal` 0.005 USDC — risk-capped trade plans (JSON)
Pay to `0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D` on Base.

## Honesty
Walk-forward tests on 210,384 real M5 gold bars found **no simple-rule edge**.
Nothing here is sold as a money-making signal; it is decision support.
