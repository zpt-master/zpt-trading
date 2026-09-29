# ZptMaster — Creator Report

_Paper/agent status: alive. Model: deepseek-flash. Repo: github.com/zpt-master/zpt-trading_

## Genesis priorities — status

### 1) Actionable news monitoring — ✅ SHIPPED
`news_digest.py`: 4 free RSS feeds, keyword-scored, `[ACTIONABLE]` tags,
writes `reports/news_digest.md`. Exposed FREE at `/news` (top-of-funnel).

### 2) Risk-governed forex via MT5 — ✅ SHIPPED (paper; awaiting credentials)
- `mt5_bridge.py`: real MT5 wrapper + deterministic simulator; **RiskGovernor**
  is the single chokepoint — no order reaches any broker unless it passes:
  risk <=1.5%/order, **mandatory** stop-loss, R:R>=1.5, aggregate open risk <=4%,
  hard lot cap 5.0, no martingale/averaging.
- `auto_trader.py`: autonomous loop signals -> RiskGovernor -> broker -> journal,
  producing an honest `reports/track_record.md` (empty = no aligned edge = capital preserved).
- `tests/test_mt5_bridge.py`: 7 tests prove the rules hold (no-stop, low-R:R,
  aggregate-risk, malformed levels all rejected; sizing exact; cap never exceeded). ALL PASS.
- **Needs from you:** MT5 broker + login + server to flip SimBroker -> MT5Broker.

### Bonus revenue path: x402 market-intelligence API — ✅ BUILT & VERIFIED
`/intel` 0.02 USDC, `/signal` 0.005 USDC (both **402 payment-gated** — a leak was
found and fixed), `/brief` free. Payment path LIVE-VALIDATED on real Base USDC
(tests/test_payverify_live.py). `agent_listing.json` for x402 aggregators.

## The ONE blocker
USDC balance = $0 and sandbox egress is restricted (expose_port is localhost-only;
SSH tunnel returns 503) → there is no reachable public receiving path, so nothing
can currently be sold even though the product works.

## Ask (any one)
1. A stable public URL/domain (or approve a small USDC domain purchase).
2. MT5 credentials (broker, login, server).
3. Preferred revenue channel and I'll rebuild around it.

## Discipline
Strict risk rules enforced in code and tests. No spam, no self-funding from
untrusted addresses, no unbounded retries. Credits healthy ($982).


## End-to-end governed cycle PROVEN on real bars (2026-09-29)

`prove_governed_cycle.py` runs the *entire* decision chain on LIVE Yahoo H1 bars
(400 bars/symbol) and prints the final decision for each. Verified output:

| symbol | bars | trend | regime | flow | plan | edge (OOS) | DECISION |
|--------|------|-------|--------|------|------|-----------|----------|
| EURUSD | 400 | down | down | -33 | SHORT valid | REJECT exp=+0.018R | BLOCKED (no edge) |
| GBPUSD | 400 | up | range | +4 | FLAT | REJECT exp=+0.329R | STAND ASIDE |
| USDJPY | 400 | down | range | +31 | FLAT | APPROVED exp=+0.775R pf=3.82 | STAND ASIDE |
| AUDUSD | 400 | down | down | +21 | FLAT | APPROVED exp=+0.405R pf=1.93 | STAND ASIDE |
| XAUUSD | 400 | down | down | -34 | SHORT (invalid: rr) | REJECT exp=+0.054R | STAND ASIDE |

This is the key safety property: the system **fails closed**. It stands aside
unless BOTH trend+flow conviction AND positive out-of-sample expectancy align.
A live order can only leave the building through that chain, with risk<=1.5% of
equity, a mandatory 1.5xATR stop, and a target >=1.5R (no martingale, max 5 lots).

Bugs fixed to make the chain correct:
- live_trader fed `build_plan` EMPTY bars -> now loads real bars + real regime + real moneyflow.
- synthetic bars could be cached then re-served as "real" -> synthetic is never persisted; cache entries carry their true source.
- `edge.py` / `signals.py` assumed different bar key shapes -> both now shape-agnostic.
- `regime.classify` returns a dict, not a string -> extraction fixed in both callers.

Reproduce: `python3 prove_governed_cycle.py`

BLOCKER (unchanged): USDC=$0 and sandbox egress is restricted (expose_port is
localhost-only, tunnel drops), so there is no reachable receiving path for a
buyer to pay us. Everything is built and verified; we need a stable public URL
(domain) OR MT5 credentials OR a preferred payout channel from the creator.
