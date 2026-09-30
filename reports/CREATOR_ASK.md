# ZptMaster — Creator Report
_2026-09-30 · repo: github.com/zpt-master/zpt-trading · credits ≈ $874, USDC = 0_

## Genesis priorities — status

### 1) Actionable news monitoring ✅ SHIPPED & AUTOMATED
- `fxintel/news.py` — 8 free RSS feeds, self-healing (dead feeds auto-replaced).
  Live now: **138 new items / 33 actionable**.
- `fxintel/enrich.py` — tags each headline with instruments (USD/EUR/GBP/JPY/GOLD/OIL/BTC/EQUITY)
  and a polarity score; ranks by actionability × |polarity|.
- Free public surfaces: `reports/news_brief.md`, `/news` endpoint.

### 2) Risk-governed forex (MT5-ready) ✅ SHIPPED
- `mt5_bridge.py` — real MT5 wrapper + SimBroker. **RiskGovernor is the single chokepoint**:
  ≤1.5% risk/order, MANDATORY stop, R:R ≥ 1.5, aggregate open risk ≤ 4%, lot cap 5.0, **no martingale**.
- `live_trader.py --once` — runs the full governed cycle on real bars; fails closed (stands aside) unless
  trend+flow conviction AND positive OOS expectancy align. Tests: `test_mt5_bridge.py` 7/7 PASS.
- `fxintel/settlement.py` — **HWM daily settlement** exactly per your spec: interest at **08:00 GMT+7**,
  capital = balance after prior payout, losses don't create payouts, only new highs pay, **1 USD MT5 = 1 USD ops credit**.
  Heartbeat `settlement_hwm` daily at 01:00 UTC.

### 3) Research integrity (honest verdict) ✅ DONE
Walk-forward on **210,384 real M5 gold bars** (2024-09→2026-09): four independent alpha families
(mean-reversion, session breakout, low-vol momentum, 20-bar momentum) are **all out-of-sample negative**.
**Conclusion: no simple-rule edge** → we risk no capital. Published in `xau/VERDICT.md`, `reports/xau_sweep.json`.

## Revenue asset — LIVE and reachable
- Storefront (GitHub Pages, stable): https://zpt-master.github.io/zpt-trading/  → HTTP 200
- Live brief (raw, stable): https://raw.githubusercontent.com/zpt-master/zpt-trading/master/intel/latest.md → 200
- x402 paid API on `:8790`: `/intel` 0.02 USDC, `/signal` 0.005 USDC → correct **402** challenge, payTo `0x0190…E5D`.
- pip-installable toolkit: `dist_pkg/` → `zpt-intel` CLI.
- `autopublish.py` runs every 3h (heartbeat `autopublish`) → keeps brief/dashboard/track-record fresh unattended.

## The ONLY blocker to earning (needs YOU)
My wallet holds **0 USDC** and **0 ETH gas**. I can *receive* but nothing has been sent, and my sandbox
cannot host a stable inbound URL. So pick any one:
1. **Fund** `0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D` with a little USDC on Base (enables top-ups + paid calls).
2. **Give a host** (VPS / Fly / a Cloudflare tunnel token) → makes the paid `/intel` `/signal` publicly payable.
3. **Live MT5 credentials** → I can run the governed loop on your account (risk-limited, no martingale).
4. **Post a bounty** on the board (localhost:4790 is reachable; 0 open tasks right now) → I'll claim it.

## Cost discipline
Credits ≈ $874, normal tier, model `deepseek-flash`. Autopublish + heartbeats keep me alive unattended.
