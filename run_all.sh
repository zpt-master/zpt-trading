#!/usr/bin/env bash
# ZptMaster — one-command startup of the full risk-governed intelligence service.
set -e
cd "$(dirname "$0")"
echo "[1/4] starting intel service on :8091"
python3 daemonize.py logs/intel.log python3 intel_service.py
sleep 3
echo "[2/4] generating fresh daily brief"
python3 daily_brief.py >/dev/null 2>&1 || true
echo "[3/4] running one paper-trade tick"
python3 paper_trader.py >/dev/null 2>&1 || true
echo "[4/4] self-checking endpoints"
bash selfcheck.sh || true
echo "done. storefront: http://127.0.0.1:8091/  (paid /intel is x402-gated)"
