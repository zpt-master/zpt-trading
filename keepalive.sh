#!/usr/bin/env bash
cd /home/oroth/trading
pgrep -f intel_server.py >/dev/null || nohup python3 intel_server.py >> reports/intel_server.log 2>&1 &
