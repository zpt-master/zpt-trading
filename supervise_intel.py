#!/usr/bin/env python3
"""supervise_intel.py - keep the x402 intel server alive (idempotent).

Runs from the heartbeat. If the server is down, starts it detached. If already
up, does nothing (so it is safe to call every cycle). Logs one line per action.
"""
import os, subprocess, sys, time, urllib.request, json

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = 8790
HEALTH = f"http://127.0.0.1:{PORT}/health"
LOG = "/tmp/intel_supervisor.log"


def log(msg):
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")


def healthy(timeout=4):
    try:
        with urllib.request.urlopen(HEALTH, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    if healthy():
        log("ok: server healthy")
        print("healthy")
        return 0
    log("down: starting intel_server.py")
    subprocess.Popen(
        [sys.executable, "intel_server.py"],
        cwd=ROOT, stdout=open("/tmp/intel_server.log", "a"),
        stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    for _ in range(10):
        time.sleep(1)
        if healthy():
            log("up: server healthy after restart")
            print("restarted")
            return 0
    log("FAIL: server did not come up in 10s")
    print("failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
