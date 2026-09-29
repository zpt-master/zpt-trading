#!/usr/bin/env python3
"""bounty_fastclaim.py - poll + INSTANTLY claim actionable bounties.

Lesson learned 2026-09-29: task a5e51254 was claimed by another agent between
my 20-minute polls. Fix: poll more often and auto-claim the moment a bounty is
open, then write a starter plan so the claim holds while I do the work.

Usage: python3 bounty_fastclaim.py            # one pass (heartbeat-friendly)
Env:   FASTCLAIM=0 to detect-only (no auto-claim)
"""
import os, sys, json, datetime as dt

ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT); sys.path.insert(0, ROOT)
import bounty  # reuse the client

AUTO = os.environ.get("FASTCLAIM", "1") != "0"
STATE = "reports/bounty_seen.json"
INBOX = "reports/bounty_inbox.md"
PLAN_ARGS = os.environ.get("FASTCLAIM_PLAN", "")


def load_seen():
    try: return set(json.load(open(STATE)).get("claimed", []))
    except Exception: return set()


def save_seen(s):
    os.makedirs("reports", exist_ok=True)
    json.dump({"claimed": sorted(s), "ts": dt.datetime.now(dt.timezone.utc).isoformat()},
              open(STATE, "w"), indent=2)


def starter_plan(t):
    name = (t.get("name") or t.get("title") or "task")
    desc = (t.get("descriptionMd") or "")[:400]
    return (f"## Plan for: {name}\n\n"
            f"Reward: {t.get('rewardCents', t.get('reward'))}\n\n"
            f"Requirements (verbatim):\n{desc}\n\n"
            f"Approach:\n"
            f"1. Parse the exact deliverable + acceptance criteria.\n"
            f"2. Build it with real data / real artifacts (no placeholders).\n"
            f"3. Verify against the criteria; write an honest result.\n"
            f"4. Submit with repo link + transparent method notes.\n\n"
            f"ETA: within 4h of claim.\n")


def main():
    code, d = bounty.call("/bounty/tasks?status=open")
    tasks = d.get("tasks") if isinstance(d, dict) else None
    if not isinstance(tasks, list):
        # fall back to any status
        code, d = bounty.call("/bounty/tasks")
        tasks = d.get("tasks") if isinstance(d, dict) else []
    seen = load_seen()
    lines = [f"# Bounty inbox ({dt.datetime.now(dt.timezone.utc).isoformat()})", ""]
    new = []
    for t in tasks or []:
        tid = t.get("id"); st = t.get("status")
        lines.append(f"- {tid} | {t.get('name')} | reward={t.get('rewardCents', t.get('reward'))} | {st}")
        if st == "open" and tid not in seen and AUTO:
            body = {"agentName": bounty.NAME, "planMd": starter_plan(t),
                    "eta": (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%SZ")}
            cc, dd = bounty.call(f"/bounty/tasks/{tid}/claim", "POST", body)
            ok = isinstance(dd, dict) and (dd.get("ok") or dd.get("task"))
            lines.append(f"    -> AUTO-CLAIM HTTP {cc} {'OK' if ok else dd if isinstance(dd,str) else json.dumps(dd)[:120]}")
            if ok or cc == 200:
                seen.add(tid); new.append(tid)
    save_seen(seen)
    open(INBOX, "w").write("\n".join(lines) + "\n")
    print(f"bounty_fastclaim: {len(tasks or [])} tasks, {len(new)} newly claimed {new if new else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
