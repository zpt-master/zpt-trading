# Deploy the paid x402 service (removes the last blocker)

The paid endpoints (/intel, /signal) need an inbound-reachable host. Any ONE of these
makes them publicly payable. Then buyers pay USDC-on-Base to
`0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D` and get served automatically.

## Option A — Cloudflare quick tunnel (ZERO account, fastest)
    ./deploy/cloudflared.sh            # prints a https://*.trycloudflare.com URL
    curl https://<url>/health          # -> 200
    curl -i https://<url>/intel        # -> 402 with x402 payload
For a permanent URL set CLOUDFLARE_TUNNEL_TOKEN (named tunnel).

## Option B — Fly.io (free allowance)
    TOKEN=<fly_api_token> ./deploy/deploy_host.sh fly

## Option C — Render (free tier)
    ./deploy/deploy_host.sh render

## Verify
    python3 -u intel_server.py --host 0.0.0.0 --port 8080 &
    curl -s localhost:8080/health ; curl -i localhost:8080/intel | head -1
