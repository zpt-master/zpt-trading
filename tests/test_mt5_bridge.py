#!/usr/bin/env python3
"""Unit tests for the MT5 risk-governed execution bridge (no live account)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mt5_bridge import (RiskGovernor, Rules, OrderRequest, SimBroker, execute,
                        size_position, pip_size)

def test_sizing_is_exact():
    lots = size_position(10000.0, 1.5, 20 * pip_size("EURUSD"), "EURUSD", Rules())
    assert lots == 0.75, lots
    print("  PASS sizing exact ->", lots, "lots risking $150")

def test_governor_rejects_no_stop():
    gov = RiskGovernor()
    d = gov.review(OrderRequest("EURUSD", "buy", 1.10, 1.10, 1.11, 10000.0))
    assert not d.approved and "stop" in d.reason.lower(), d
    print("  PASS no-stop rejected:", d.reason)

def test_governor_rejects_bad_rr():
    gov = RiskGovernor(Rules(min_rr=1.5)); px = 1.10
    d = gov.review(OrderRequest("EURUSD", "buy", px, px - 20*0.0001, px + 10*0.0001, 10000.0))
    assert not d.approved and "R:R" in d.reason, d
    print("  PASS low-R:R rejected:", d.reason)

def test_governor_rejects_aggregate_risk():
    gov = RiskGovernor(Rules(max_open_risk_pct=4.0, max_risk_pct=1.5)); px = 1.10
    d = gov.review(OrderRequest("EURUSD", "buy", px, px - 20*0.0001, px + 45*0.0001,
                                10000.0, open_risk_pct=3.0))
    assert not d.approved and "aggregate" in d.reason, d
    print("  PASS aggregate-risk rejected:", d.reason)

def test_governor_rejects_wrong_levels():
    gov = RiskGovernor()
    d = gov.review(OrderRequest("EURUSD", "buy", 1.10, 1.11, 1.12, 10000.0))
    assert not d.approved, d
    print("  PASS malformed levels rejected:", d.reason)

def test_approved_order_places_in_sim():
    b = SimBroker(equity=10000.0); gov = RiskGovernor()
    px = b.price("EURUSD"); pip = pip_size("EURUSD")
    req = OrderRequest("EURUSD", "buy", px, round(px - 20*pip, 5), round(px + 45*pip, 5),
                       10000.0, comment="t")
    out = execute(b, req, gov)
    assert out["result"] == "placed", out
    assert out["decision"]["lots"] == 0.74, out["decision"]
    assert b.open_risk_pct() <= 1.5 + 1e-6, b.open_risk_pct()
    print("  PASS approved & placed; open risk =", b.open_risk_pct(), "%")

def test_never_exceeds_max_risk_under_many_orders():
    b = SimBroker(equity=10000.0); gov = RiskGovernor(Rules(max_open_risk_pct=4.0))
    placed = 0
    for _ in range(10):
        px = b.price("EURUSD"); pip = pip_size("EURUSD")
        req = OrderRequest("EURUSD", "buy", px, round(px - 20*pip, 5), round(px + 45*pip, 5),
                           10000.0, open_risk_pct=b.open_risk_pct(), comment="loop")
        if execute(b, req, gov)["result"] == "placed":
            placed += 1
        assert b.open_risk_pct() <= 4.0 + 1e-6, b.open_risk_pct()
    assert placed >= 1
    print("  PASS %d orders placed, open risk capped at %s%% (never >4%%)" % (placed, b.open_risk_pct()))

if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    print("running %d MT5-bridge tests" % len(fns))
    for f in fns:
        f()
    print("ALL MT5 BRIDGE TESTS PASSED")
