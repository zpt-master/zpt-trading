#!/usr/bin/env bash
# Render/any-PaaS start: bind public host, use $PORT
set -e
exec python3 -u "$(dirname "$0")/../intel_server.py" --host 0.0.0.0 --port "${PORT:-8080}"
