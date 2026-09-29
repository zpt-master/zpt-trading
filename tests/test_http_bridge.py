#!/usr/bin/env python3
"""End-to-end test: HttpMT5Broker talks to a mock MT5 bridge server,
and the SAME RiskGovernor still gates every order."""
import os, sys, json, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from mock_mt5_server import HTTPServer, H
from mt5_bridge import HttpMT5Broker, RiskGovernor, OrderRequest, execute

def start():
    srv = HTTPServer(("127.0.0.1", 5057), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.3)
    return srv

def main():
    srv = start()
    cfg = {"base_url":"http://127.0.0.1:5057","api_key":"",
           "paths":{"account":"/account","price":"/price","order":"/order",
                    "close":"/close","positions":"/positions"}}
    b = HttpMT5Broker(cfg)
    h = b.health(); assert h["ok"], h
    print("  PASS health ->", h["account"])
    acct = b.account(); assert acct["equity"] == 10000.0, acct
    print("  PASS account ->", acct)
    px = b.price("EURUSD"); assert abs(px - 1.10) < 1e-6, px
    print("  PASS price EURUSD ->", round(px,5))
    gov = RiskGovernor()
    pip = 0.0001
    req = OrderRequest("EURUSD","buy", round(px,5), round(px-20*pip,5),
                       round(px+45*pip,5), 10000.0, comment="http-test")
    out = execute(b, req, gov)
    assert out["result"] == "placed", out
    assert out["broker"]["ticket"], out
    print("  PASS governed order placed via HTTP bridge ->", out["broker"]["ticket"],
          "lots", out["decision"]["lots"])
    # Governor still enforces: no-stop must be rejected BEFORE hitting the bridge
    bad = OrderRequest("EURUSD","buy", px, px, px+30*pip, 10000.0)
    assert execute(b, bad, gov)["result"] == "rejected"
    print("  PASS no-stop rejected (never reached the bridge)")
    srv.shutdown()
    print("ALL HTTP BRIDGE TESTS PASSED")

if __name__ == "__main__":
    main()
