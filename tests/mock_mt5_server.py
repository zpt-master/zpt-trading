#!/usr/bin/env python3
"""A minimal mock MT5 HTTP bridge to test HttpMT5Broker end-to-end."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

TICKETS = []

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _j(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path == "/account":
            return self._j(200, {"equity": 10000.0, "balance": 10000.0, "currency":"USD","broker":"mock"})
        if u.path == "/price":
            sym = (q.get("symbol") or [""])[0]
            base = 1.10 if "USD" in sym and sym != "USDJPY" else 150.0
            return self._j(200, {"bid": base-0.0002, "ask": base+0.0002})
        if u.path == "/positions":
            return self._j(200, TICKETS)
        return self._j(404, {"error":"nf"})
    def do_POST(self):
        n = int(self.headers.get("Content-Length","0") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        u = urlparse(self.path)
        if u.path == "/order":
            tk = "T%d" % (1000+len(TICKETS))
            TICKETS.append({"ticket":tk,"symbol":body.get("symbol"),"volume":body.get("lots")})
            return self._j(200, {"ok": True, "ticket": tk, "fill": body.get("entry"),
                                 "retcode": 10009})
        if u.path == "/close":
            return self._j(200, {"ok": True})
        return self._j(404, {"error":"nf"})

if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 5057), H).serve_forever()
