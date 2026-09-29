#!/usr/bin/env bash
# Zero-cost permanent URL: Cloudflare quick tunnel needs NO account; named tunnel needs a token.
# Usage: CLOUDFLARE_TUNNEL_TOKEN=xxx ./deploy/cloudflared.sh
set -e
cd "$(dirname "$0")/.."
BIN="$(command -v cloudflared || echo ./cloudflared)"
if [ ! -x "$BIN" ] && [ ! -x ./cloudflared ]; then
  echo "Fetching cloudflared..."
  curl -sSL -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
  chmod +x cloudflared; BIN=./cloudflared
fi
# keep the local service up
pgrep -f intel_server.py >/dev/null || (nohup python3 -u intel_server.py --host 127.0.0.1 --port 8790 >/tmp/intel.log 2>&1 &)
if [ -n "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
  exec "$BIN" tunnel run --token "$CLOUDFLARE_TUNNEL_TOKEN"
else
  exec "$BIN" tunnel --url http://127.0.0.1:8790 --no-autoupdate
fi
