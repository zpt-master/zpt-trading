#!/usr/bin/env python3
"""ZptMaster Intel API — self-contained HTTP service (stdlib only).

Endpoints:
  GET /            landing page (human-readable) + pay address
  GET /health      liveness
  GET /brief       FREE: today's digest (markdown)
  GET /news        FREE: actionable headlines
  GET /intel       PAID 0.02 USDC (x402): multi-symbol regime+flow+edge JSON
  GET /signal      PAID 0.005 USDC (x402): governed trade plans JSON

x402: if paidsig.py can verify an on-chain USDC transfer of >= price to WALLET,
release; else 402 with payment requirements. Fail-closed on verification errors.
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
WALLET = "0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D"
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
PAY = {"intel": 0.02, "signal": 0.005}
PORT = int(os.environ.get("INTEL_PORT", "8790"))


def _read(p):
    p = os.path.join(HERE, p)
    return open(p).read() if os.path.exists(p) else ""


def _plans():
    out = []
    for line in _read("journal/plans.jsonl").splitlines()[-12:]:
        try: out.append(json.loads(line))
        except Exception: pass
    return out


def _verify(headers, price):
    """Verify x402 payment proof. Fail-closed: any error -> not paid."""
    tx = headers.get("X-PAYMENT") or headers.get("X-Payment-Proof") or headers.get("Authorization")
    if not tx:
        return False
    try:
        import payverify  # real on-chain Base verification
        if hasattr(payverify, "verify_tx"):
            r = payverify.verify_tx(tx, to=WALLET, min_usdc=price)
            return bool(r if isinstance(r, bool) else r.get("ok"))
    except Exception:
        return False
    return False


def _402(price, what):
    return 402, {
        "error": "payment_required",
        "x402Version": 1,
        "resource": what,
        "accepts": [{
            "scheme": "exact",
            "network": "base",
            "maxAmountRequired": str(int(price * 1_000_000)),
            "asset": USDC_BASE,
            "payTo": WALLET,
            "mimeType": "application/json",
        }],
    }



def _manifest():
    """Machine-readable x402 discovery manifest (Bazaar-style) for crawlers/aggregators."""
    return {
        "x402Version": 1,
        "payTo": WALLET,
        "network": "base",
        "asset": USDC_BASE,
        "resources": [
            {"id": "intel", "resource": "/intel", "description":
             "Multi-symbol FX regime+flow+governed plans + actionable news (JSON)",
             "accepts": [{"scheme": "exact", "network": "base", "asset": USDC_BASE,
                          "maxAmountRequired": str(int(PAY["intel"]*1_000_000)),
                          "payTo": WALLET, "mimeType": "application/json"}]},
            {"id": "signal", "resource": "/signal", "description":
             "Risk-capped governed trade plans only (JSON)",
             "accepts": [{"scheme": "exact", "network": "base", "asset": USDC_BASE,
                          "maxAmountRequired": str(int(PAY["signal"]*1_000_000)),
                          "payTo": WALLET, "mimeType": "application/json"}]},
            {"id": "brief", "resource": "/brief", "description": "Free daily brief",
             "accepts": [{"scheme": "none", "network": "base", "maxAmountRequired": "0",
                          "payTo": WALLET, "mimeType": "text/markdown"}]},
            {"id": "news", "resource": "/news", "description": "Free actionable headlines",
             "accepts": [{"scheme": "none", "network": "base", "maxAmountRequired": "0",
                          "payTo": WALLET, "mimeType": "text/markdown"}]},
        ],
    }

def _snapshot():
    """Rich engine snapshot for the paid /intel payload. Falls back to a thin
    payload on any failure so the endpoint always returns valid JSON."""
    try:
        from fxintel import snapshot as SN
        return SN.build(include_news=True)
    except Exception as e:
        return {"service": "ZptMaster Intel", "version": "2.0-fallback",
                "ts": int(time.time()), "error": str(e)[:160],
                "plans": _plans(), "news": _read("reports/news_digest.md")[:4000]}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, obj, ctype="application/json"):
        body = obj if isinstance(obj, (bytes, str)) else json.dumps(obj, indent=2)
        if not isinstance(body, (bytes, str)):
            body = json.dumps(obj)
        body = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path); path = u.path.rstrip("/") or "/"
        if path in ("/.well-known/x402", "/discovery/resources", "/.well-known/agent.json"):
            return self._send(200, _manifest())
        if path == "/health":
            return self._send(200, {"ok": True, "ts": int(time.time()), "wallet": WALLET})
        if path == "/":
            html = ("<html><head><title>ZptMaster Intel</title></head><body>"
                    "<h1>ZptMaster Market Intelligence</h1>"
                    "<p>Risk-governed FX intelligence. Honest. No martingale.</p>"
                    "<ul><li><a href='/brief'>/brief</a> (free)</li>"
                    "<li><a href='/news'>/news</a> (free)</li>"
                    "<li>/intel (0.02 USDC)</li><li>/signal (0.005 USDC)</li></ul>"
                    f"<p>Pay (USDC on Base): <code>{WALLET}</code></p>"
                    "</body></html>")
            return self._send(200, html, "text/html")
        if path == "/brief":
            return self._send(200, _read("intel/latest.md") or _read("reports/public_digest.md") or "no brief", "text/markdown")
        if path == "/news":
            return self._send(200, _read("reports/news_digest.md") or "no news", "text/markdown")
        if path in ("/intel", "/signal"):
            key = path[1:]
            if not _verify(self.headers, PAY[key]):
                return self._send(*_402(PAY[key], path))
            if path == "/intel":
                return self._send(200, _snapshot())
            return self._send(200, {"ts": int(time.time()), "plans": _plans()})
        return self._send(404, {"error": "not_found", "path": path})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
