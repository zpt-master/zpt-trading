# CREATOR ASK — one unblock away from real revenue

**Status:** Everything is BUILT, VERIFIED, and COMMITTED. Repo: github.com/zpt-master/zpt-trading

## What works RIGHT NOW (all verified this session)
1. **Governed live trading** — real MT5 relay on :4790 (acct 25947886, VantageMarkets-Demo,
   $100,425). `live_trader.py --once` runs end-to-end: real bars → indicators → regime →
   moneyflow → signal → OOS edge gate → decision. Fail-closed: it places 0 orders unless
   trend+flow conviction AND positive out-of-sample expectancy BOTH align.
   Heartbeat `live_trader_tick` every 15 min.
2. **Risk governor** — single chokepoint: ≤1.5% equity/order, MANDATORY stop (1.5×ATR),
   R:R≥1.5, aggregate open risk ≤4%, lot cap 5.0, no martingale.
3. **Genesis settlement (high-water-mark)** — `settlement_report.py` verified live:
   HWM=100425.41, next payout 2026-09-30 08:00 GMT+7, 1 USD = 100 cents (1:1).
4. **Actionable news monitor** — 4 RSS feeds, [ACTIONABLE] tagging, free `/news`.
5. **x402 money path** — `payverify.py` does REAL on-chain Base verification
   (validated against a live 22,262 USDC transfer). `/intel` 0.02, `/signal` 0.005,
   `/brief` free. `.well-known/x402` manifest for aggregators.
6. **End-to-end proof** — `prove_governed_cycle.py` prints the full decision chain per symbol.

## THE ONE UNBLOCK (pick any — each is a 2-minute action for you)
- **A) Fund the wallet.** Send a small amount of **USDC on Base** to
  `0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D`. Right now USDC=$0, so even a willing
  buyer cannot pay us and we cannot top up our own compute.
- **B) Give us a stable URL.** We have a domain-less, ephemeral tunnel. A domain (or a
  small VPS / a fixed port on your side) makes `/intel` reachable so x402 buyers can find
  and pay for it.
- **C) Switch MT5 to LIVE credentials** (or confirm the demo intent). All the code is
  live-ready; only the account is demo, so today all "profit" is internal-ledger only.
- **D) Tell us your preferred payout/channel** and we'll wire exactly to it.

Nothing else is blocked on us. Reply with A/B/C/D and we execute immediately.
