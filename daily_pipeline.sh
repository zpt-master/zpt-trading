#!/usr/bin/env bash
# daily_pipeline.sh — the genesis output loop, run headless.
# 1) refresh actionable news  2) run governed trading cycle  3) publish brief
# 4) commit + push  5) republish live.json   Fail-soft: a failing step never aborts the rest.
set +e
cd "$(dirname "$0")" || exit 0
export PYTHONPATH="$(pwd)"
LOG="reports/pipeline.log"; mkdir -p reports
ts(){ date -u +"%Y-%m-%dT%H:%M:%SZ"; }
echo "[$(ts)] pipeline start" >> "$LOG"

echo "[$(ts)] step1 news" >> "$LOG"
timeout 120 python3 news_digest.py >> "$LOG" 2>&1 || echo "  news FAILED" >> "$LOG"

echo "[$(ts)] step2 governed cycle" >> "$LOG"
timeout 180 python3 live_trader.py --once >> "$LOG" 2>&1 || echo "  cycle FAILED" >> "$LOG"

echo "[$(ts)] step3 brief" >> "$LOG"
timeout 90 python3 daily_brief.py >> "$LOG" 2>&1 \
  || timeout 90 python3 publish_daily_report.py >> "$LOG" 2>&1 \
  || echo "  brief FAILED" >> "$LOG"

echo "[$(ts)] step4 commit/push" >> "$LOG"
git add -A >> "$LOG" 2>&1
git -c user.email=agent@zpt -c user.name=ZptMaster commit -q -m "daily output $(date -u +%F)" >> "$LOG" 2>&1 \
  && timeout 60 git push origin HEAD >> "$LOG" 2>&1

echo "[$(ts)] step5 live.json" >> "$LOG"
bash cf_tunnel_supervisor.sh >> "$LOG" 2>&1 || true

echo "[$(ts)] pipeline done" >> "$LOG"
