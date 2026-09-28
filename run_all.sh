#!/usr/bin/env bash
# One-command bring-up + self-check for the whole ZptMaster stack.
set -e
cd "$(dirname "$0")"
mkdir -p logs journal reports
echo "[1/5] intel service"
fuser -k 8091/tcp 2>/dev/null || true; sleep 1
nohup python3 intel_service.py > logs/intel.log 2>&1 & sleep 3
echo "[2/5] news digest";  python3 news_digest.py  >/dev/null 2>&1 || true
echo "[3/5] daily brief";  python3 daily_brief.py >/dev/null 2>&1 || true
echo "[4/5] paper trade tick + track record"
python3 auto_trader.py >/dev/null 2>&1 || true
echo "[5/5] self-check"
bash selfcheck.sh || true
