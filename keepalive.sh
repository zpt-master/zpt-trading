#!/bin/sh
cd /home/oroth/trading || exit 0
curl -s -m 5 -o /dev/null http://127.0.0.1:8091/health && exit 0
python3 daemonize.py logs/intel.log python3 intel_service.py
