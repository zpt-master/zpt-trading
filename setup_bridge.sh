#!/usr/bin/env bash
# One-command MT5 bridge configurator.
#   ./setup_bridge.sh <base_url> [api_key]
# Example:
#   ./setup_bridge.sh http://172.27.176.1:5000
# Writes config/mt5.json and runs a live preflight. Fail-closed on bad URL.
set -e
cd "$(dirname "$0")"
URL="${1:-${MT5_BRIDGE_URL:-}}"
KEY="${2:-${MT5_API_KEY:-}}"
if [ -z "$URL" ]; then
  echo "usage: ./setup_bridge.sh <base_url> [api_key]"
  echo "   or: export MT5_BRIDGE_URL=http://host:port && ./setup_bridge.sh"
  exit 2
fi
mkdir -p config
cat > config/mt5.json <<JSON
{
  "mode": "http",
  "live": false,
  "base_url": "${URL%/}",
  "api_key": "${KEY}",
  "symbol_suffix": "",
  "timeout": 10,
  "paths": {"account":"/account","price":"/price","order":"/order","close":"/close","positions":"/positions"}
}
JSON
echo "wrote config/mt5.json -> $URL"
echo "=== preflight ==="
python3 live_trader.py --preflight || true
echo
echo "If preflight is OK: set \"live\": true in config/mt5.json to arm real orders."
echo "Safety: daily-loss limit 5%, kill-switch = touch DISABLE_LIVE, or MT5_KILL=1."
