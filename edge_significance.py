#!/usr/bin/env python3
"""edge_significance.py - is the candidate edge statistically real, or noise?

The paper-forward run showed expectancy +0.2245%/trade over 218 trades. Before
risking ONE cent of capital we must ask: could this be luck? This tool answers
that with two independent resampling tests, both fail-closed.

Inputs:  journal/paper_forward.jsonl (per-trade R multiples)
Method:
  1. Non-parametric bootstrap (10k) -> 95% CI for expectancy and profit factor.
  2. Sign-permutation test (10k)    -> p-value that mean R > 0 by chance.
Verdict: GO-TO-PAPER only if CI lower bound > 0 AND p < 0.05.
         Else NO EDGE-PROVEN -> keep capital safe, keep paper-testing.
Output: reports/edge_significance.json
"""
from __future__ import annotations
import os, sys, json, random, datetime as dt, statistics as st

ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
LOG = "journal/paper_forward.jsonl"
OUT = "reports/edge_significance.json"
NBOOT = 10000
NPERM = 10000
RISK_PCT = 1.0


def load_returns():
    rs = []
    if os.path.exists(LOG):
        for line in open(LOG):
            line = line.strip()
            if not line: continue
            try:
                rs.append(float(json.loads(line)["R"]))
            except Exception:
                pass
    return rs


def pf(rs):
    w = sum(r for r in rs if r > 0)
    l = abs(sum(r for r in rs if r <= 0))
    return w / l if l > 0 else float("inf")


def bootstrap(rs, n=NBOOT, seed=42):
    rnd = random.Random(seed)
    N = len(rs)
    means, pfs = [], []
    for _ in range(n):
        s = [rs[rnd.randrange(N)] for _ in range(N)]
        means.append(sum(s) / N)
        pfs.append(pf(s))
    means.sort(); pfs.sort()
    lo = int(0.025 * n); hi = int(0.975 * n)
    return {
        "exp_mean_pct": round(sum(rs) / N * RISK_PCT, 4),
        "exp_ci95": [round(means[lo] * RISK_PCT, 4), round(means[hi] * RISK_PCT, 4)],
        "pf_point": round(pf(rs), 3),
        "pf_ci95": [round(pfs[lo], 3), round(pfs[hi], 3)],
    }


def permutation(rs, n=NPERM, seed=7):
    """H0: returns are symmetric noise (mean 0). Flip signs randomly."""
    rnd = random.Random(seed)
    obs = sum(rs) / len(rs)
    absr = [abs(r) for r in rs]
    count = 0
    for _ in range(n):
        s = sum(rnd.choice((1, -1)) * a for a in absr) / len(rs)
        if s >= obs: count += 1
    return {"observed_mean_R": round(obs, 4), "p_value": round((count + 1) / (n + 1), 4)}


def main():
    rs = load_returns()
    os.makedirs("reports", exist_ok=True)
    if len(rs) < 50:
        out = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(), "trades": len(rs),
               "verdict": "INSUFFICIENT SAMPLE (<50) - keep paper-testing, no capital"}
        json.dump(out, open(OUT, "w"), indent=2); print(json.dumps(out, indent=2)); return
    b = bootstrap(rs); p = permutation(rs)
    proven = b["exp_ci95"][0] > 0 and p["p_value"] < 0.05
    out = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(), "trades": len(rs),
           "bootstrap": b, "permutation": p,
           "verdict": ("EDGE STATISTICALLY PROVEN - advance to a true forward paper window only"
                       if proven else
                       "EDGE NOT PROVEN (CI includes 0 or p>=0.05) - keep capital safe, continue paper-testing")}
    json.dump(out, open(OUT, "w"), indent=2)
    print(f"trades={len(rs)}")
    print(f"expectancy {b['exp_mean_pct']}%/trade  CI95={b['exp_ci95']}")
    print(f"profit factor {b['pf_point']}  CI95={b['pf_ci95']}")
    print(f"permutation p-value={p['p_value']}")
    print("VERDICT:", out["verdict"])


if __name__ == "__main__":
    main()
