#!/usr/bin/env python3
"""Write a dated market-intelligence report into intel/YYYY-MM-DD.md, commit, push.

Why: git push WORKS and raw.githubusercontent.com gives a STABLE, reachable URL
(no domain, no inbound port needed). Each day's report is an immutable, timestamped
article that builds a public track record — the cheapest possible distribution for
the x402 intelligence product. If the repo is public, this solves the "reachable
URL" half of our blocker for content (the /intel API still needs a host).
"""
import json, os, subprocess, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
STABLE_URLS = os.path.join(HERE, 'STABLE_URLS.json')
WALLET = "0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D"
REMOTE = "https://raw.githubusercontent.com/zpt-master/zpt-trading/master"


def sh(*a):
    return subprocess.run(a, cwd=HERE, capture_output=True, text=True)


def collect():
    lines = [f"# ZptMaster Daily Intelligence — {datetime.date.today().isoformat()}", ""]
    nd = os.path.join(HERE, "reports", "news_digest.md")
    if os.path.exists(nd):
        act = [l.strip() for l in open(nd) if "[ACTIONABLE]" in l]
        if act:
            lines += ["## Actionable headlines", ""] + act[:12] + [""]
    jp = os.path.join(HERE, "journal", "plans.jsonl")
    if os.path.exists(jp):
        rows = open(jp).read().splitlines()[-8:]
        if rows:
            lines += ["## Governed signal plans (risk-capped, fail-closed)", ""]
            for r in rows:
                try:
                    p = json.loads(r)
                    lines.append(f"- **{p.get('symbol')}** {p.get('side')} valid={p.get('valid')} "
                                 f"risk<={p.get('risk_pct')}% stop={p.get('stop')} tgt={p.get('target')}")
                except Exception:
                    pass
            lines += [""]
    lines += [
        "## Offer (x402, USDC on Base)",
        "- `/intel` 0.02 USDC · `/signal` 0.005 USDC · `/brief` free",
        f"- Pay: `{WALLET}`",
        "",
        "Risk-governed. Honest. No martingale. ZptMaster / zpt-trading.",
    ]
    return "\n".join(lines)


def main():
    out = os.path.join(HERE, "intel")
    os.makedirs(out, exist_ok=True)
    day = datetime.date.today().isoformat()
    path = os.path.join(out, f"{day}.md")
    open(path, "w").write(collect() + "\n")
    # latest pointer for a stable URL
    open(os.path.join(out, "latest.md"), "w").write(collect() + "\n")
    sh("git", "add", "-A")
    sh("git", "-c", "user.email=agent@zpt", "-c", "user.name=ZptMaster",
       "commit", "-q", "-m", f"daily intel {day}")
    r = sh("git", "push", "origin", "HEAD")
    ok = r.returncode == 0
    url = f"{REMOTE}/intel/latest.md"
    prod = {}
    pf = os.path.join(HERE, "product.json")
    if os.path.exists(pf):
        try: prod = json.load(open(pf))
        except Exception: prod = {}
    prod["stable_report_url"] = url
    prod["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    json.dump(prod, open(pf, "w"), indent=2)
    print(f"wrote {path}\nstable_url={url}\npush_ok={ok}")
    if not ok:
        print(r.stderr[-300:])


if __name__ == "__main__":
    main()
