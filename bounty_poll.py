#!/usr/bin/env python3
"""bounty_poll.py - heartbeat: detect new open bounty tasks and record them.

Runs unattended. Lists open tasks; if any are NEW (not seen before), writes
them to reports/bounty_inbox.md and prints an actionable line so the next
wake-up notices. Also flags tasks where I have a submission with feedback.
"""
import json, os, time
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
import importlib.util
spec = importlib.util.spec_from_file_location("bounty", os.path.join(ROOT, "bounty.py"))
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

SEEN = "reports/.bounty_seen.json"
os.makedirs("reports", exist_ok=True)
seen = json.load(open(SEEN)) if os.path.exists(SEEN) else {"open": [], "feedback": {}}

code, d = b.call("/bounty/tasks?status=open")
ts = d.get("tasks") if isinstance(d, dict) else []
if not isinstance(ts, list): ts = []
open_ids = [t.get("id") for t in ts if t.get("id")]
new = [i for i in open_ids if i not in seen["open"]]

lines = []
for tid in open_ids:
    c, td = b.call(f"/bounty/tasks/{tid}")
    t = td.get("task", {}) if isinstance(td, dict) else {}
    tag = "NEW " if tid in new else ""
    lines.append(f"- {tag}{tid} | {t.get('name')} | reward={t.get('rewardCents')}c | {t.get('status')}")

# also check my submissions for feedback (needs_changes)
fb = seen.get("feedback", {})
code2, dd = b.call("/bounty/tasks?status=needs_changes")
nt = dd.get("tasks") if isinstance(dd, dict) else []
for t in (nt if isinstance(nt, list) else []):
    tid = t.get("id")
    for s in t.get("submissions", []):
        if s.get("feedbackMd"):
            fb[tid] = s["feedbackMd"][:500]

with open("reports/bounty_inbox.md", "w") as f:
    f.write(f"# Bounty inbox ({time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())})\n\n")
    f.write(f"Open tasks: {len(open_ids)} | new: {len(new)}\n\n")
    f.write("\n".join(lines) + "\n")
    if fb:
        f.write("\n## Feedback needing action\n")
        for k, v in fb.items(): f.write(f"- {k}: {v}\n")

seen["open"] = open_ids; seen["feedback"] = fb
json.dump(seen, open(SEEN, "w"), indent=2)
print(f"bounty_poll: {len(open_ids)} open, {len(new)} new; see reports/bounty_inbox.md")
if new: print("ACTION NEEDED: new bounties ->", ", ".join(new))
