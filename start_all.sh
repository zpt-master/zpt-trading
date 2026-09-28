#!/usr/bin/env bash
cd "$(dirname "$0")"
pkill -f trade_loop.sh 2>/dev/null; pkill -f report_loop.sh 2>/dev/null
sleep 1
setsid ./trade_loop.sh  </dev/null >/dev/null 2>&1 &
setsid ./report_loop.sh </dev/null >/dev/null 2>&1 &
sleep 1
echo "started: $(pgrep -fc 'trade_loop.sh|report_loop.sh') loop processes"
