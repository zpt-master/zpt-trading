#!/usr/bin/env bash
cd "$(dirname "$0")"
while true; do python3 news.py >> logs/news.log 2>&1; sleep 1800; done
