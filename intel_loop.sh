#!/usr/bin/env bash
cd "$(dirname "$0")"
while true; do
  if ! pgrep -f intel_service.py >/dev/null; then setsid python3 intel_service.py </dev/null >>logs/intel.log 2>&1 & fi
  sleep 300
done
