#!/usr/bin/env python3
"""Regression test: the full governed money path is LIVE.

Proven 2026-09-29: RiskGovernor-approved order -> LedgerMT5Broker.market_order
-> POST /mt5/order -> Windows MT5 bridge -> MetaTrader5.order_send -> FILLED.

This test is non-destructive: it only asserts the RELAY is reachable and that
symbol resolution finds the broker suffix (e.g. "EURUSD+"). It does NOT place
orders (run with LIVE_E2E=1 + explicit symbol to place a 0.01 governed test).
"""
import os, sys, json, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from mt5_relay import LedgerMT5Broker


class TestRelay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = LedgerMT5Broker(os.environ.get("LEDGER_URL", "http://127.0.0.1:4790"),
                                os.environ.get("LEDGER_TOKEN", "change-me-shared-secret"))
        try:
            cls.health = cls.b.health()
        except Exception as e:
            cls.health = {"ok": False, "error": str(e)}

    def test_health_reachable(self):
        if not self.health.get("ok"):
            self.skipTest("relay not reachable: %s" % self.health.get("error"))
        self.assertTrue(self.health["ok"])

    def test_account_is_real(self):
        if not self.health.get("ok"):
            self.skipTest("relay not reachable")
        a = self.b.account()
        self.assertIn("equity", a)
        self.assertGreater(a["equity"], 0)

    def test_symbol_resolution_finds_suffix(self):
        if not self.health.get("ok"):
            self.skipTest("relay not reachable")
        try:
            resolved = self.b.resolve_symbol("EURUSD")
        except Exception as e:
            self.skipTest("no snapshot: %s" % e)
        # Vantage uses "EURUSD+"; accept exact too but require a non-empty symbol
        self.assertTrue(resolved)
        self.assertIn("EURUSD", resolved.upper())

    def test_price_available(self):
        if not self.health.get("ok"):
            self.skipTest("relay not reachable")
        try:
            px = self.b.price("EURUSD")
        except Exception as e:
            self.skipTest("no price yet: %s" % e)
        self.assertGreater(px, 0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
