#!/usr/bin/env bash
# Keeps the local x402 service + a Cloudflare quick tunnel alive, and PUBLISHES the
# current public URL to the repo's stable surfaces whenever it changes. Idempotent.
set -u
cd "$(dirname "$0")"

# 1) local service
if ! pgrep -f "intel_server.py" >/dev/null; then
  nohup python3 -u intel_server.py --host 127.0.0.1 --port 8790 >/tmp/intel.log 2>&1 &
  sleep 2
fi

# 2) cloudflared binary
BIN=./cloudflared
[ -x "$BIN" ] || { curl -sSL -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && chmod +x cloudflared; }

# 3) tunnel
if ! pgrep -f "cloudflared tunnel --url" >/dev/null; then
  rm -f /tmp/cf.log
  nohup "$BIN" tunnel --url http://127.0.0.1:8790 --no-autoupdate >/tmp/cf.log 2>&1 &
fi

# 4) discover current public URL
URL=""
for i in $(seq 1 15); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/cf.log 2>/dev/null | head -1)
  [ -n "$URL" ] && break
  sleep 2
done
[ -z "$URL" ] && { echo "no tunnel url"; exit 1; }

# 5) verify it actually serves
CODE=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 15 "$URL/health" 2>/dev/null || echo 000)
if [ "$CODE" != "200" ]; then echo "tunnel url not healthy ($CODE): $URL"; exit 1; fi

# 6) publish if changed
OLD=$(cat PUBLIC_URL.txt 2>/dev/null || echo "")
echo "$URL" > PUBLIC_URL.txt
echo "PUBLIC_URL=$URL (changed=$([ "$URL" != "$OLD" ] && echo yes || echo no))"
if [ "$URL" != "$OLD" ] || [ ! -f docs/live.json ]; then
  mkdir -p docs/.well-known
  python3 - "$URL" <<'PY'
import json,sys,datetime
u=sys.argv[1]
d={"live_base_url":u,"health":u+"/health","intel":u+"/intel","signal":u+"/signal",
   "brief":u+"/brief","news":u+"/news","x402_manifest":u+"/.well-known/x402",
   "wallet":"0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D","network":"base","asset":"USDC",
   "updated":datetime.datetime.utcnow().isoformat()+"Z",
   "note":"Ephemeral quick-tunnel URL; auto-republished on change by cf_tunnel_supervisor.sh"}
json.dump(d,open("docs/live.json","w"),indent=2)
print("wrote docs/live.json")
PY
  git add -A
  git -c user.email=agent@zpt -c user.name=ZptMaster commit -q -m "live: public x402 base url -> $URL" 2>/dev/null
  timeout 40 git push origin HEAD >/dev/null 2>&1 && echo "published $URL" || echo "push failed"
fi
exit 0
