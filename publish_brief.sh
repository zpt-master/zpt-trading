#!/usr/bin/env bash
# Publish today's brief to a public URL (paste.rs) and record it.
cd "$(dirname "$0")"
URL=$(timeout 30 curl -s --data-binary "@reports/latest.md" https://paste.rs)
if [[ "$URL" == https://paste.rs/* ]]; then
  echo "$URL" > reports/.latest_url
  python3 - "$URL" <<'PY'
import json,sys,os
u=sys.argv[1]
p="product.json"; cfg=json.load(open(p)) if os.path.exists(p) else {}
cfg["brief_url"]=u; json.dump(cfg,open(p,"w"),indent=2)
PY
  echo "published: $URL"
else
  echo "publish failed: $URL"
fi
