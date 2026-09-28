#!/bin/bash
# Keeps a localhost.run tunnel to :8091 alive; writes the live URL to public_url.txt.
cd "$(dirname "$0")"
URL=$(cat public_url.txt 2>/dev/null)
healthy=$(curl -s -m 8 -o /dev/null -w "%{http_code}" "${URL}/health" 2>/dev/null)
if [ "$healthy" = "200" ]; then exit 0; fi
pkill -f 'nokey@localhost.run' 2>/dev/null
sleep 1
nohup ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes \
  -R 80:localhost:8091 nokey@localhost.run > logs/tunnel.log 2>&1 &
sleep 12
NEW=$(grep -oE 'https://[a-z0-9-]+\.lhr\.life' logs/tunnel.log | tail -1)
[ -n "$NEW" ] && echo "$NEW" > public_url.txt && echo "tunnel up: $NEW"
