"""zpt-intel CLI: build a fused actionable market brief locally. Stdlib only."""
import argparse, datetime as dt, json, sys

DISCLAIMER = ("Informational only. Not financial advice. "
              "No trading edge is claimed; strategy research is published honestly.")


def build_brief(news_md: str, market: list) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [f"# ZptIntel Brief — {now}", "", "## Actionable drivers"]
    for a in (news_md or "").splitlines():
        if a.startswith("- **["):
            out.append(a)
    out += ["", "## Market view"]
    out.append("```json\n" + json.dumps(market[:5], indent=2) + "\n```" if market
               else "_No aligned signal._")
    out += ["", DISCLAIMER]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="zpt-intel", description="Build an actionable market brief")
    ap.add_argument("--news", default="", help="path to news brief markdown")
    ap.add_argument("--market", default="", help="path to market signals JSON")
    ap.add_argument("--out", default="-", help="output path (default stdout)")
    a = ap.parse_args(argv)
    news = open(a.news).read() if a.news else ""
    try:
        market = json.load(open(a.market)) if a.market else []
    except Exception:
        market = []
    brief = build_brief(news, market)
    if a.out == "-":
        sys.stdout.write(brief + "\n")
    else:
        open(a.out, "w").write(brief)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
