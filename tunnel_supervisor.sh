#!/bin/sh
cd /home/oroth/trading || exit 0
while true; do
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
      -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes \
      -R 80:localhost:8091 nokey@localhost.run >> logs/tunnel.log 2>&1
  grep -oE 'https://[a-z0-9.-]+\.lhr\.life' logs/tunnel.log | tail -1 > PUBLIC_URL.txt
  sleep 10
done
