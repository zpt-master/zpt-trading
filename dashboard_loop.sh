#!/usr/bin/env bash
cd "$(dirname "$0")"
while true; do
  if ! pgrep -f dashboard.py >/dev/null; then setsid python3 dashboard.py </dev/null >>logs/dashboard.log 2>&1 & fi
  sleep 300
done
