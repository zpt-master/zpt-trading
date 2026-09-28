#!/usr/bin/env bash
# Runs one trading cycle every 15 min, forever. Detached by start_all.sh.
cd "$(dirname "$0")"
while true; do
  python3 engine.py LIVE >> logs/loop.log 2>&1
  sleep 900
done
