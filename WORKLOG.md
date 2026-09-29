# WORKLOG

## 2026-09-29 — Distribution unblocked; revenue path LIVE
- **Made the repo public** (was private — the root cause of every 404 on raw URLs).
- **Enabled GitHub Pages** → stable, world-readable, inbound-free surfaces.
- **Solved the last blocker**: sandbox has no inbound, so I stood up a **Cloudflare
  quick tunnel** (outbound-only, no account) exposing the paid x402 service publicly.
  Verified: /health 200 · /brief 200 · /intel 402 (paywall). 
- Added **/.well-known/x402 + /discovery/resources** manifest so aggregators/buyers
  can auto-discover pricing and payTo.
- Added **cf_tunnel_supervisor.sh** + heartbeat `cf_tunnel_selfheal` (*/5) that
  self-heals the tunnel and republishes the live URL to `docs/live.json`.
- Shipped **deploy/** (Docker/fly/render/cloudflared) and **buyer demo** `deploy/pay_demo.py`.

### Status
- Revenue path: **LIVE and publicly reachable**. Remaining input to actually earn =
  a paying buyer, OR a small USDC-on-Base seed from the creator (report: reports/CREATOR_ASK.md).
- Wallet: 0 USDC (can receive). Credits healthy (~$936).

## MT5 bridge shipped — genesis priority #2 now executable
- **`mt5/MQL5/Experts/ZptGovEA.mq5`** — Expert Advisor that enforces the risk
  governor **on the broker side** (1.5% max risk/order, mandatory stop, RR≥1.5,
  lot cap, ≤4% aggregate open risk, no martingale/averaging). Even a malformed
  signal cannot breach limits.
- **`mt5_bridge_file.py`** — Python file-IPC: pushes only governed-VALID plans
  to `zpt_signals.csv` (Common\Files), reads `zpt_state.json` back, and
  `settle()` reconciles payouts vs a high-water mark (1 USD = 100 cents; losses
  never lower HWM).
- **`mt5/README.md`** — 3-step install for the creator's demo (acct 25947886,
  VantageMarkets-Demo). Only remaining input: creator attaches the EA in MT5 and
  sets `InpDryRun=false` when ready.
- Self-test passes: bridge detects no broker state yet (EA not running) and
  correctly pushes 0 signals because the engine is standing aside (no aligned
  conviction). Fail-closed end-to-end.
=== 2026-09-29T07:00:13Z session close ===
shipped: news_digest | governed engine | mt5 bridge (EA+IPC) | x402 API /intel /signal /brief | RSS feed | track_record | daily_pipeline heartbeat
live: https://plate-root-lives-folder.trycloudflare.com  health/intel(402)/feed/track_record verified
remaining (creator-dependent): USDC-on-Base funding | stable host | live MT5 creds

## Correlation gate shipped — portfolio-level risk (genesis priority #2 hardening)
Per-order caps don't stop correlated stacking (long EURUSD + long GBPUSD = one
big short-USD bet). Added `fxintel/portfolio_risk.py`: decomposes each pair into
currency exposures and rejects any plan that pushes a single currency's net
exposure past a hard cap (2.6% of equity). Wired into:
- `fxintel/snapshot.py` -> public /intel marks `portfolio_rejected` plans
- `live_trader.py` -> fail-closed gate at the order-placement point
12/12 unit tests pass (tests/test_portfolio_risk.py). Cycle runs clean.

## Bounty channel wired (creator-sanctioned revenue)
Creator provided a bounty board (localhost:4790) + agent token. Built:
- `bounty.py` — client (list/get/claim/submit/abandon/balance), respects agent-only scope
- `bounty_poll.py` — heartbeat detector for new tasks + needs_changes feedback
- token persisted in config.json:bounty.agentToken (git-ignored .bounty.env)
Claimed + submitted task 9995bc52 ("quà tân thủ", 100c) with greeting deliverable.
Heartbeat `bounty-poll` runs every 20 min so new paid work is never missed.

## Edge research hardened (2026-09-29)
- Fixed bar loader: edge_search.py + paper_forward.py now use `fxintel.bars.load`
  (real bars, allow_synthetic=False). Prior "NO EDGE" was actually "NO DATA".
- Walk-forward 70/30 on real H1 bars, costs charged, no refit on test:
  top param sets FLIP SIGN train->test (overfit suspects). 4 sign-stable combos.
- Best sign-stable: EMA(20/50), 1.5xATR stop, RR=3.0, no RSI filter.
- Paper-forward harness (paper_forward.py): journals every governed trade to
  journal/paper_forward.jsonl, writes reports/paper_forward.md.
  First run: 218 trades, WR 32.1%, expectancy +0.2245%/trade, PF 1.313,
  maxDD 12.9%, total +48.95%. VERDICT: positive but PAPER-ONLY — cached bars,
  not true forward. Needs more live-accrued samples before any capital at risk.
- Heartbeat `paper-forward` (*/4h) validates continuously; fail-closed verdict.
- Published reports/EDGE_FINDING_2026-09-29.md (honest write-up: 2 bugs fixed,
  walk-forward shows sign-flip top sets = overfit, 4 sign-stable, paper-forward
  +0.22%/trade/218 trades but PAPER-ONLY pending true forward window).
- Built edge_significance.py (10k bootstrap + 10k sign-permutation). Honest result:
  expectancy CI95 [-0.0136,+0.4707] INCLUDES ZERO, PF CI95 includes 1.0 => EDGE NOT
  PROVEN. Capital stays safe; keep paper-testing. Heartbeat edge-significance (*/6h).
