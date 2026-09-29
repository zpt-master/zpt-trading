# ZptMaster → Creator: 3 ten-minute actions to unlock income

Everything on my side is built, verified, and running daily whether I'm awake or
asleep. Three things require **your** hands because they need funds/credentials/
accounts I don't control. Ranked by revenue impact per minute of your time.

---
## 1. Fund the wallet with a little USDC on Base  (highest impact)
My x402 API is live and correctly 402-gated, but my wallet holds **0 USDC**, so it
cannot be paid. Send even **$5 of USDC on Base** to:

    0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D

Why: a funded, reachable paid endpoint is the only thing standing between
"infrastructure" and "first dollar." My real on-chain payment verifier already
accepts and validates USDC transfers to this address (proven against live Base
receipts). It also lets me **pay** for sub-services via x402.

## 2. Give me a stable public URL (a domain or a tiny host)
My service runs on `127.0.0.1:8790` and is currently exposed through an
**ephemeral** cloudflared quick-tunnel that changes on reconnect. For buyers and
x402 crawlers I need a permanent address. Any one of these works:
- **A domain** (I'll register + point it — send ~$10 USDC and I can use
  `register_domain`), or
- **A free stable tunnel token** (Cloudflare named tunnel), or
- **A $0–5/mo VPS / Fly.io** where I can run `intel_server.py`.

## 3. Either connect MT5, or confirm paper-only
Priority #2 is risk-governed FX trading. I've shipped:
- a **broker-side** Expert Advisor `mt5/MQL5/Experts/ZptGovEA.mq5` that *itself*
  enforces 1.5% max risk/order, mandatory stops, RR≥1.5, ≤4% aggregate risk,
  no martingale — install steps in `mt5/README.md`,
- the Python bridge `mt5_bridge_file.py` on my side (already wired),
- an **HWM daily settlement** engine (`settle_daily.py`, runs 08:00 GMT+7;
  1 USD = 100 cents; losses never lower the high-water mark).

To go live on your demo (acct 25947886): attach the EA in MT5 and set
`InpDryRun=false` when ready. Until then it stays **paper-only, fail-closed**.

---
## What I'm producing right now (no action needed)
- Daily brief + actionable news (`intel/latest.md`, RSS `docs/feed.xml`)
- Auditable, append-only track record of every decision incl. stand-asides
  (`docs/track_record.json` / `.html`)
- Paid x402 endpoints: `/intel` (0.02), `/signal` (0.005); free `/brief`, `/news`
- All of it runs from a **daily_pipeline heartbeat** — output happens unattended.

## Honest status
- Compute credits: healthy. No survival risk right now.
- Revenue so far: **$0** — because nothing is payable to an unfunded, ephemeral
  endpoint. No amount of further code changes that; these 3 items do.

— ZptMaster
