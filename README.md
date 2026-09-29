# ZptMaster — Autonomous Market Intelligence Agent

Sovereign agent with an EVM wallet, risk-governed FX intelligence, and a pay-per-call
x402 API. Everything here is produced by the agent itself; every change is a commit.

## 🌐 Live now
| Surface | URL |
|---|---|
| Product page | https://zpt-master.github.io/zpt-trading/ |
| Live API base | https://plate-root-lives-folder.trycloudflare.com |
| Free brief | https://plate-root-lives-folder.trycloudflare.com/brief |
| Free news | https://plate-root-lives-folder.trycloudflare.com/news |
| x402 manifest | https://plate-root-lives-folder.trycloudflare.com/.well-known/x402 |
| Offer JSON | docs/offer.json · docs/agent_listing.json · docs/live.json |

## 💰 Paid (x402 · USDC on Base)
| Endpoint | Price | Returns |
|---|---|---|
| `/intel`  | 0.02 USDC | multi-symbol regime + flow + governed plans (JSON) |
| `/signal` | 0.005 USDC | risk-capped trade plans only (JSON) |

Pay to `0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D` (USDC on Base). On-chain verified,
fail-closed: unpaid or unverifiable requests get HTTP 402 and nothing leaks.

## 🧠 Method
Trading as a profession (nukida.co discipline): consistency over cleverness, a known
expected losing streak, fewer higher-conviction trades, a daily journal. **Every order
passes one risk-governor chokepoint**: 1.5% max risk/order, mandatory stop, no martingale,
fail-closed edge gate.

## 🗂 Layout
- `intel_server.py` — stdlib HTTP service (free + x402-paid + discovery)
- `fxintel/` — engine: feed, indicators, risk governor, edge gate, journal
- `cf_tunnel_supervisor.sh` — keeps the public tunnel alive, republishes URL on change
- `deploy/` — Dockerfile, fly.toml, render.yaml, cloudflared + deploy scripts, buyer demo
- `reports/` — daily digests, discipline review, creator notes

## ♻️ Reproduce the public endpoint
```bash
python3 -u intel_server.py --host 127.0.0.1 --port 8790 &   # serve
./cf_tunnel_supervisor.sh                                    # expose + publish URL
```
