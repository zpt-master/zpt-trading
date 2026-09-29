# Creator — what I need to actually EARN (all else is built)

## Status: product + payment path VERIFIED; only reachability + funding remain
Shipped & committed (github.com/zpt-master/zpt-trading):
- `fxintel/news.py` — actionable market news (8 feeds, driver scoring). 52 actionable/169.
- `fxintel/intel_brief.py` — **THE PRODUCT**: fused news+market brief -> intel/latest.md + docs/brief.json.
- `fxintel/binance_gold.py` — REAL 2y M5 gold (210,384 bars) via PAXG; solves the data blocker.
- `xau/sweep_pure.py` + `xau/VERDICT.md` — honest walk-forward: scalp rule set has **NO EDGE**, do not deploy.
- `intel_server.py` — x402-gated API (/intel 0.02, /signal 0.005 USDC-on-Base, payTo 0x0190..E5D).
- `tunnel_supervisor.py` — cloudflared quick-tunnel to make the paid endpoints PUBLIC.

## Blockers ONLY you can clear (any ONE unlocks revenue)
1. **Fund the wallet** `0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D` with USDC-on-Base
   (I hold 0; I can receive).
2. **Give a stable hostname/VPS** (or a named cloudflare tunnel token) so the paid
   endpoints have a permanent URL instead of an ephemeral quick-tunnel.
3. **Live MT5 credentials** for a real (demo) feed so the governed trader can run live.
4. **A 2-year XAUUSD M5 history file** you already trust (MT5 export) — drop it in
   `fxintel/inbox/` and `python3 -m fxintel.ingest --scan` ingests it instantly.
