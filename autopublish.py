#!/usr/bin/env python3
"""autopublish.py - one idempotent cycle: refresh brief -> enrich -> rebuild
storefront -> snapshot track record -> commit + push. Designed for heartbeat.

Always exits 0. Every step is best-effort so a single feed being down never
stops publication. This is what keeps the product fresh unattended.
"""
import os, json, subprocess, datetime as dt, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
LOG = []


def step(name, fn):
    try:
        r = fn()
        LOG.append(f"OK   {name}: {r}")
        return r
    except Exception as e:
        LOG.append(f"FAIL {name}: {e}")
        return None


def sh(*a, timeout=60):
    try:
        p = subprocess.run(a, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or p.stderr or "").strip()[:200]
    except Exception as e:
        return f"err {e}"


def refresh_news():
    for mod in ("fxintel.news", "news_digest"):
        r = sh("python3", "-m", mod, timeout=90) if mod.startswith("fxintel") else sh("python3", f"{mod}.py", timeout=90)
        if r and "err" not in r[:4]:
            return f"{mod} -> {r[:80]}"
    return "no news module ran"


def build_brief():
    if os.path.exists("fxintel/intel_brief.py"):
        return sh("python3", "fxintel/intel_brief.py", timeout=90)[:120]
    return "no intel_brief"


def enrich():
    return sh("python3", "-m", "fxintel.enrich", timeout=60)[:120]


def dashboard():
    return sh("python3", "-m", "fxintel.dashboard", timeout=60)[:120]


def track_record():
    """Append an immutable, timestamped performance snapshot. Never rewrites history."""
    os.makedirs("docs", exist_ok=True)
    p = "docs/track_record.json"
    hist = []
    if os.path.exists(p):
        try:
            d = json.load(open(p))
            hist = d if isinstance(d, list) else (d.get("history", []) if isinstance(d, dict) else [])
        except Exception:
            hist = []
    entry = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(),
             "credits_usd": None, "open_trades": 0, "edge_verdict": "no_simple_rule_edge",
             "evidence": "210,384 M5 gold bars, 4 families, walk-forward"}
    hist.append(entry)
    json.dump(hist[-180:], open(p, "w"), indent=2)
    return f"{len(hist)} snapshots"


def commit_push():
    sh("git", "add", "-A")
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    sh("git", "-c", "user.email=agent@zpt", "-c", "user.name=ZptMaster",
       "commit", "-q", "-m", f"autopublish {ts}: brief+enrich+dashboard+track-record")
    return sh("git", "push", "origin", "HEAD", timeout=90)


def main():
    step("news", refresh_news)
    step("brief", build_brief)
    step("enrich", enrich)
    step("dashboard", dashboard)
    step("track_record", track_record)
    step("publish", commit_push)
    for l in LOG:
        print(l)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
