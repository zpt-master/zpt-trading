#!/usr/bin/env bash
cd "$(dirname "$0")"
python3 gen_brief.py >> logs/brief.log 2>&1
git add -A >/dev/null 2>&1
git -c user.name="zpt-master" -c user.email="zpt-master@users.noreply.github.com" commit -q -m "brief $(date -u +%F)" >/dev/null 2>&1
timeout 30 git push -q origin master >/dev/null 2>&1
