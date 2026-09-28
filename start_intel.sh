#!/usr/bin/env bash
cd "$(dirname "$0")"
PAY=$(python3 -c "import json;c=json.load(open('config.json'));print(c['x402']['pay_to'] if c['x402']['enabled'] else '')")
PRICE=$(python3 -c "import json;print(json.load(open('config.json'))['x402']['intel_price_usdc'])")
pkill -f intel_service.py 2>/dev/null; sleep 1
X402_PAY_TO="$PAY" INTEL_PRICE_USDC="$PRICE" setsid python3 intel_service.py </dev/null >>logs/intel.log 2>&1 &
sleep 2; echo "intel started pay_to=${PAY:0:10}... price=$PRICE"
