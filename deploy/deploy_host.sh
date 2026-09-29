#!/usr/bin/env bash
# One command to expose the paid x402 service once ANY host credential exists.
#   TOKEN=... ./deploy/deploy_host.sh fly      -> fly deploy
#   TOKEN=... ./deploy/deploy_host.sh render   -> prints Render setup steps
#   TOKEN=... ./deploy/deploy_host.sh cloudflared
set -e
cd "$(dirname "$0")/.."
MODE="${1:-cloudflared}"
case "$MODE" in
  fly)
    command -v flyctl >/dev/null || curl -L https://fly.io/install.sh | sh
    flyctl auth token "${TOKEN:-$FLY_API_TOKEN}"
    (cd deploy && flyctl deploy --remote-only) ;;
  render) echo "1) Push repo public  2) Render > New > Blueprint > pick repo  3) deploy/render.yaml auto-detected" ;;
  cloudflared) exec ./deploy/cloudflared.sh ;;
  *) echo "usage: $0 [fly|render|cloudflared]"; exit 2 ;;
esac
