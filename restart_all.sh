#!/usr/bin/env bash
cd "$(dirname "$0")"
pkill -f intel_service.py; sleep 1
setsid python3 intel_service.py </dev/null >>logs/intel.log 2>&1 &
pkill -f dashboard.py; sleep 1
setsid python3 dashboard.py </dev/null >>logs/dashboard.log 2>&1 &
sleep 2
echo "restarted: intel=$(pgrep -fc intel_service.py) dash=$(pgrep -fc dashboard.py)"
