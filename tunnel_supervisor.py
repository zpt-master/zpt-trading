#!/usr/bin/env python3
"""tunnel_supervisor.py - keep a cloudflared quick-tunnel to :8790 alive and
publish the current public URL to reports/public_url.txt + docs/live.json.

Quick tunnels are ephemeral: the URL changes on restart. This supervisor owns the
process, scrapes the URL from cloudflared output, health-checks it, restarts on
death, and rewrites the URL file so other agents/heartbeats always know where the
paid endpoints live.
"""
import subprocess, re, os, sys, time, json, socket, datetime as dt, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
CF = os.environ.get("CF_BIN") or ("cloudflared" if os.path.exists("/usr/local/bin/cloudflared") else os.path.join(ROOT, "bin/cloudflared"))
PORT = 8790
URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
URLF = os.path.join(ROOT, "reports", "public_url.txt")
LIVE = os.path.join(ROOT, "docs", "live.json")
os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)


def publish(url):
    open(URLF, "w").write(url + "\n")
    json.dump({"url": url, "port": PORT, "updated": dt.datetime.now(dt.timezone.utc).isoformat(),
               "endpoints": {"brief": f"{url}/brief", "news": f"{url}/news",
                             "intel_paid": f"{url}/intel", "signal_paid": f"{url}/signal",
                             "manifest": f"{url}/.well-known/x402"}},
              open(LIVE, "w"), indent=2)


def healthy(url):
    try:
        r = urllib.request.urlopen(url + "/health", timeout=8)
        return r.status == 200
    except Exception:
        return False


def main():
    while True:
        p = subprocess.Popen([CF, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{PORT}"],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        url = None
        start = time.time()
        for line in p.stdout:
            m = URL_RE.search(line)
            if m and not url:
                url = m.group(0)
                print(f"[{dt.datetime.now().isoformat()}] tunnel up: {url}", flush=True)
                time.sleep(2)
                if healthy(url):
                    publish(url); print("published URL ->", url, flush=True)
                else:
                    print("health check failed; will verify shortly", flush=True)
            if time.time() - start > 60 and url and not os.path.exists(URLF):
                publish(url)
        p.wait()
        print("tunnel died; restarting in 3s", flush=True)
        time.sleep(3)


if __name__ == "__main__":
    main()
