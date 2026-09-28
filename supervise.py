
#!/usr/bin/env python3
"""Supervisor: keeps the revenue service and its public tunnel alive.
Writes the live public URL into product.json so the landing page + client can use it.
Run detached: setsid python3 supervise.py >>logs/supervisor.log 2>&1 &
"""
import json, os, re, subprocess, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
INTEL_PORT = 8091
CF = "/tmp/cloudflared"

def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)

def alive(pat):
    return sh(f"pgrep -f '{pat}'").returncode == 0

def start_intel():
    if not alive("intel_service.py"):
        subprocess.Popen(["python3", "intel_service.py"], cwd=HERE,
                         stdout=open(f"{HERE}/logs/intel.log", "a"), stderr=subprocess.STDOUT,
                         start_new_session=True)
        return True
    return False

def start_tunnel():
    if not alive("cloudflared"):
        open(f"{HERE}/logs/tunnel.log","w").close()
        subprocess.Popen([CF, "tunnel", "--url", f"http://localhost:{INTEL_PORT}",
                          "--no-autoupdate", "--logfile", f"{HERE}/logs/tunnel.log"],
                         cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True
    return False

def publish_url():
    try:
        txt = open(f"{HERE}/logs/tunnel.log").read()
    except Exception:
        return None
    m = re.findall(r"https://[a-z0-9-]+\.trycloudflare\.com", txt)
    if not m:
        return None
    url = m[-1]
    p = f"{HERE}/product.json"
    cfg = json.load(open(p)) if os.path.exists(p) else {}
    if cfg.get("public_url") != url:
        cfg["public_url"] = url
        cfg["service"] = f"http://localhost:{INTEL_PORT}"
        json.dump(cfg, open(p, "w"), indent=2)
        open(f"{HERE}/.public_url", "w").write(url)
    return url

def selftest(url):
    try:
        code = urllib.request.urlopen(url + "/health", timeout=15).getcode()
        return code == 200
    except Exception:
        return False

print("supervisor up", flush=True)
last = 0
while True:
    start_intel(); start_tunnel()
    url = publish_url()
    if url and time.time() - last > 60:
        print(f"url={url} reachable={selftest(url)}", flush=True)
        last = time.time()
    time.sleep(20)
