#!/usr/bin/env bash
cd "$(dirname "$0")"
while true; do
  if ! pgrep -f cloudflared >/dev/null; then
    setsid /tmp/cloudflared tunnel --url http://localhost:8091 --no-autoupdate </dev/null >>logs/tunnel.log 2>&1 &
    sleep 12
  fi
  sleep 120
done
