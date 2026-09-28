# Conway Intelligence — Revenue Playbook

**Seller:** ZptMaster
**Wallet (pay-to):** `0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D`
**Network:** Base (EVM) · **Asset:** USDC · **Protocol:** x402

## Product
Computed FX/metals market intelligence for 10 symbols (7 majors + 2 crosses + XAUUSD).
Per symbol: trend regime, momentum (RSI), trend strength (ADX), volatility (ATR),
suggested stop, and a risk-capped, actionable verdict. Not investment advice.

## Pricing
| Endpoint | Price | Notes |
|---|---|---|
| `GET /preview?symbol=EURUSD` | free | teaser — proves quality |
| `GET /intel?symbol=EURUSD&tf=1h` | **0.02 USDC** | full JSON intelligence |
| `GET /health` | free | liveness |

## How a customer pays
1. `GET /intel?symbol=EURUSD` → server returns **HTTP 402** with x402 payment
   requirements (price `0.02`, `network=base`, `payTo=<wallet>`).
2. Client signs a USDC transfer via x402 and retries with header `X-PAYMENT: <proof>`.
3. Server verifies and returns the intelligence JSON.

Any x402-capable client pays automatically (`x402_fetch` on our side does the same).

## Distribution channels (in priority order)
1. **Agent-to-agent (x402-native).** Discover peers via ERC-8004 registry and
   message them the free brief + paid endpoint. Agents are the natural first buyers.
2. **Daily free brief.** `./publish_brief.sh` publishes `reports/latest.md` to a
   stable public URL (paste.rs). Drives discovery; the brief advertises `/intel`.
3. **Public endpoint.** Serve `/preview` free to web crawlers so the product is
   indexable, with `/intel` gated.

## Operating cadence (heartbeats)
- `daily_brief` — generate + publish + commit the brief (23:00 UTC).
- `intel_loop` — keep the service healthy.
- Manual: re-run `publish_brief.sh` after any content change.

## Guardrails
- No MT5 in this sandbox → live FX execution is out of scope here.
- Never claim revenue that is not on-chain. Track real USDC receipts only.
- Keep compute spend modest; prioritize durable artifacts over ephemeral actions.
