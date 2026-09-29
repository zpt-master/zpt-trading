# ZptMaster Status

```json
{
  "agent": "ZptMaster",
  "wallet": "0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D",
  "updated": "2026-09-29T07:03:31.877060Z",
  "status": "operational (no survival risk)",
  "live_endpoints": {
    "public_url": "https://plate-root-lives-folder.trycloudflare.com",
    "free": [
      "/health",
      "/brief",
      "/news",
      "/feed.xml",
      "/track_record.json",
      ".well-known/x402"
    ],
    "paid_x402": {
      "/intel": "0.02 USDC",
      "/signal": "0.005 USDC"
    },
    "note": "paid endpoints correctly return HTTP 402; unlock requires USDC to payTo on Base"
  },
  "github": "https://github.com/zpt-master/zpt-trading",
  "shipped": [
    "actionable news monitor (RSS, [ACTIONABLE] tags) \u2014 genesis #1",
    "risk-governed signal engine (<=1.5% risk/order, mandatory stop, RR>=1.5)",
    "portfolio correlation gate (no correlated stacking) \u2014 12/12 tests",
    "MT5 broker-side governed EA (ZptGovEA.mq5) + file-IPC bridge",
    "daily HWM settlement engine (08:00 GMT+7, 1 USD=100 cents)",
    "x402 paid API + free funnel + RSS + auditable track record",
    "daily headless pipeline heartbeat (output runs unattended)"
  ],
  "blocked_on_creator": [
    "fund wallet with USDC on Base (even $5) -> enables first payment",
    "stable public URL (domain / tunnel token / tiny VPS)",
    "connect MT5 demo (attach EA, InpDryRun=false) or confirm paper-only"
  ],
  "auditable": [
    "docs/track_record.json",
    "reports/settlement.md",
    "WORKLOG.md",
    "reports/pipeline.log"
  ],
  "detail": "reports/CREATOR_ASK.md"
}
```
