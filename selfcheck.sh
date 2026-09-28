#!/usr/bin/env bash
# Verifies every public endpoint of the intelligence service in one shot.
B=http://127.0.0.1:8091
ck(){ code=$(curl -s -m 8 -o /dev/null -w "%{http_code}" "$B$1"); printf "  %-24s -> %s\n" "$1" "$code"; }
echo "self-check ($B)"
ck /
ck /health
ck /news
ck /brief
ck /preview
ck /.well-known/x402
ck /discovery/resources
ck /intel        # expect 402 (payment required)
ck /signal       # expect 402
