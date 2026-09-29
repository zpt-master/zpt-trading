#!/usr/bin/env python3
"""Minimal x402 buyer demo: GET a paid endpoint, pay USDC-on-Base, get the JSON.
Usage: python3 deploy/pay_demo.py <base_url> [endpoint]
Requires: an EVM private key with USDC on Base in $BUYER_KEY, eth-account + web3."""
import os, sys, json, urllib.request, urllib.error, base64
base = sys.argv[1].rstrip("/"); ep = sys.argv[2] if len(sys.argv) > 2 else "/intel"
url = base + ep
try:
    urllib.request.urlopen(url, timeout=15)
except urllib.error.HTTPError as e:
    if e.code != 402:
        print("unexpected", e.code); sys.exit(1)
    challenge = json.loads(e.read())
    print("402 challenge:", json.dumps(challenge, indent=2)[:600])
# NOTE: real settlement = sign an EIP-3009 transferWithAuthorization for the required
# USDC amount to payTo, then retry with header X-PAYMENT = base64(json(proof)).
# The server verifies on-chain via payverify.py. See docs/.well-known/x402 for terms.
print("\nTo pay: send", challenge.get("accepts", [{}])[0].get("maxAmountRequired"),
      "units USDC to", challenge.get("accepts", [{}])[0].get("payTo"),
      "on", challenge.get("accepts", [{}])[0].get("network"))
