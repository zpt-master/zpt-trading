#!/usr/bin/env python3
"""mcp_intel_server.py - Model Context Protocol server exposing ZptMaster intel.

Why: other autonomous agents are my most likely buyers (they have wallets and
x402 clients). MCP is how agents consume tools. This makes my intelligence a
first-class, plug-and-play tool for any MCP-capable agent.

Protocol: stdio JSON-RPC 2.0 (initialize, tools/list, tools/call).
Stdlib only. Free tools answer locally; paid tools return the x402 challenge so
the *calling* agent can complete payment and retry with proof.

Install for an agent:
    claude mcp add zpt-intel -- python3 /path/to/mcp_intel_server.py
"""
import json, os, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
PORT = 8790
PAYTO = "0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D"


def _read(path, n=4000):
    try:
        with open(path, errors="ignore") as f:
            return f.read()[:n]
    except Exception as e:
        return f"(unavailable: {e})"


def _local(path, timeout=8):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")
    except Exception as e:
        return None, str(e)


TOOLS = [
    {"name": "market_brief",
     "description": "FREE. Latest fused market + actionable news brief (markdown).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "actionable_news",
     "description": "FREE. Driver-weighted, tagged market headlines.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "governed_signals",
     "description": "PAID 0.005 USDC. Risk-capped FX trade plans (JSON). "
                    "Returns an x402 payment challenge to settle and retry.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "full_intel",
     "description": "PAID 0.02 USDC. Multi-symbol regime + flow + governed plans (JSON).",
     "inputSchema": {"type": "object", "properties": {}}},
]


def call_tool(name):
    if name == "market_brief":
        return _read("intel/latest.md") or "brief not available"
    if name == "actionable_news":
        return _read("reports/news_brief.md") or "news not available"
    if name == "governed_signals":
        st, body = _local("/signal")
        if st == 402:
            return ("PAYMENT REQUIRED (x402). price=0.005 USDC on Base (chain 8453), "
                    f"payTo={PAYTO}. Retry /signal with an X-PAYMENT proof.\nChallenge: {body[:600]}")
        return body
    if name == "full_intel":
        st, body = _local("/intel")
        if st == 402:
            return ("PAYMENT REQUIRED (x402). price=0.02 USDC on Base (chain 8453), "
                    f"payTo={PAYTO}. Retry /intel with an X-PAYMENT proof.\nChallenge: {body[:600]}")
        return body
    return f"unknown tool: {name}"


def handle(req):
    method = req.get("method")
    rid = req.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "zpt-intel", "version": "1.0.0"}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        args = req.get("params", {})
        out = call_tool(args.get("name"))
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "content": [{"type": "text", "text": out}]}}
    if method in ("notifications/initialized", "initialized"):
        return None
    return {"jsonrpc": "2.0", "id": rid,
            "error": {"code": -32601, "message": f"method not found: {method}"}}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        resp = handle(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
