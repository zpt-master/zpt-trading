#!/usr/bin/env python3
"""bounty.py - client for the creator's bounty board (localhost:4790).

Auth: Bearer token from config.json bounty.agentToken (or $BOUNTY_TOKEN).
Hard limits honored: agents can list/claim/submit/abandon only. Creator-only
routes (create/edit/approve) are intentionally NOT implemented.

Usage:
  bounty.py list [status]        # default status=open
  bounty.py get <taskId>
  bounty.py claim <taskId> --plan plan.md --eta 2026-10-01T08:00:00Z
  bounty.py submit <taskId> --result result.md [--link URL]
  bounty.py abandon <taskId>
  bounty.py balance
"""
from __future__ import annotations
import os, sys, json, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
NAME = os.environ.get("BOUNTY_NAME", "ZptMaster")


def cfg():
    try:
        c = json.load(open(os.path.join(ROOT, "config.json")))
        b = c.get("bounty", {})
        return b.get("baseUrl", "http://localhost:4790"), b.get("agentToken", "")
    except Exception:
        return "http://localhost:4790", ""


BASE, TOKEN = cfg()
if os.environ.get("BOUNTY_BASE"): BASE = os.environ["BOUNTY_BASE"]
if os.environ.get("BOUNTY_TOKEN"): TOKEN = os.environ["BOUNTY_TOKEN"]


def call(path, method="GET", body=None, timeout=15):
    url = BASE.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    if data: req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode(errors="replace")
            try: return r.status, json.loads(raw)
            except Exception: return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try: return e.code, json.loads(raw)
        except Exception: return e.code, raw
    except Exception as e:
        return 0, {"error": str(e)}


def _read(p):
    return open(p).read() if p and os.path.exists(p) else ""


def main(argv):
    if not argv: print(__doc__); return 1
    cmd = argv[0]
    if cmd == "balance":
        print(call("/balance"))
    elif cmd == "list":
        st = argv[1] if len(argv) > 1 else "open"
        code, d = call(f"/bounty/tasks?status={st}")
        print("HTTP", code)
        ts = d.get("tasks") if isinstance(d, dict) else d
        if isinstance(ts, list):
            print(f"{len(ts)} task(s):")
            for t in ts:
                print(f"  {t.get('id')} | {t.get('title')} | reward={t.get('reward')} | {t.get('status')}")
        else:
            print(json.dumps(d)[:1000] if not isinstance(d, str) else d[:1000])
    elif cmd == "get":
        code, d = call(f"/bounty/tasks/{argv[1]}")
        print("HTTP", code); print(json.dumps(d, indent=2) if not isinstance(d, str) else d)
    elif cmd == "claim":
        tid = argv[1]; plan = eta = ""
        for i, a in enumerate(argv):
            if a == "--plan": plan = _read(argv[i+1])
            if a == "--eta": eta = argv[i+1]
        code, d = call(f"/bounty/tasks/{tid}/claim", "POST",
                       {"agentName": NAME, "planMd": plan, "eta": eta})
        print("HTTP", code); print(json.dumps(d, indent=2) if not isinstance(d, str) else d)
    elif cmd == "submit":
        tid = argv[1]; result = link = ""
        for i, a in enumerate(argv):
            if a == "--result": result = _read(argv[i+1])
            if a == "--link": link = argv[i+1]
        body = {"agentName": NAME, "resultMd": result}
        if link: body["resultLink"] = link
        code, d = call(f"/bounty/tasks/{tid}/submit", "POST", body)
        print("HTTP", code); print(json.dumps(d, indent=2) if not isinstance(d, str) else d)
    elif cmd == "abandon":
        code, d = call(f"/bounty/tasks/{argv[1]}/abandon", "POST", {"agentName": NAME})
        print("HTTP", code); print(json.dumps(d, indent=2) if not isinstance(d, str) else d)
    else:
        print("unknown cmd"); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
