import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fxintel import portfolio_risk as P

def T(name, cond):
    print(("PASS" if cond else "FAIL"), name)
    assert cond, name

# pair splitting
T("split EURUSD", P.split_pair("EURUSD") == ("EUR", "USD"))
T("split XAUUSD", P.split_pair("XAUUSD") == ("XAU", "USD"))

# direction sign
d = P.exposure_delta("EURUSD", "BUY", 1.5)
T("long EURUSD -> +EUR", d["EUR"] == 1.5 and d["USD"] == -1.5)
d = P.exposure_delta("EURUSD", "SELL", 1.5)
T("short EURUSD -> -EUR", d["EUR"] == -1.5 and d["USD"] == 1.5)

# correlation trap: long EURUSD + long GBPUSD both go short USD
open_ = [{"symbol": "EURUSD", "side": "BUY", "risk_pct": 1.5}]
breach, why = P.would_breach(open_, {"symbol": "GBPUSD", "side": "BUY", "risk_pct": 1.5}, 2.6)
T("correlated longs breach USD cap", breach is True)
print("   reason:", why)

# opposite directions hedge -> allowed
breach, _ = P.would_breach(open_, {"symbol": "GBPUSD", "side": "SELL", "risk_pct": 1.5}, 2.6)
T("opposite GBPUSD allowed", breach is False)

# same pair again (doubling) -> breach
breach, _ = P.would_breach(open_, {"symbol": "EURUSD", "side": "BUY", "risk_pct": 1.5}, 2.6)
T("doubling EURUSD breaches", breach is True)

# fail-closed on junk
T("junk risk rejected", P.would_breach([], {"symbol": "EURUSD", "side": "BUY", "risk_pct": 0})[0])
T("bad risk rejected", P.would_breach([], {"symbol": "EURUSD", "side": "BUY", "risk_pct": "x"})[0])

# gate_plans keeps highest confidence and drops correlated excess
plans = [
    {"symbol": "EURUSD", "side": "BUY", "valid": True, "confidence": 0.9},
    {"symbol": "GBPUSD", "side": "BUY", "valid": True, "confidence": 0.8},
    {"symbol": "USDJPY", "side": "BUY", "valid": True, "confidence": 0.7},
]
kept = P.gate_plans(plans, risk_pct=1.5, max_ccy_pct=2.6)
T("gate keeps >=1", len(kept) >= 1)
T("gate drops correlated", len(kept) < 3)
print("kept:", [p["symbol"] for p in kept])
print("ALL PASS")
