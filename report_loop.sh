#!/usr/bin/env bash
# Fires the daily settlement report at 00:50 UTC (07:50 GMT+7), before the
# creator's 08:00 GMT+7 payout.
cd "$(dirname "$0")"
while true; do
  now=$(date -u +%s)
  target=$(date -u -d "today 00:50" +%s)
  [ "$target" -le "$now" ] && target=$(date -u -d "tomorrow 00:50" +%s)
  sleep $(( target - now ))
  python3 report.py >> logs/report.log 2>&1
  sleep 60
done
