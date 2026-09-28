# Verification suite for the Zpt trading + intelligence stack.
# Run: python3 tests.py   — exits nonzero on any failure. Auditable proof it works.
import json, os, sys, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
 = F = 0

def ok(name, cond, detail=""):
    global P, F
    if cond:
        P += 1; print(f"  PASS {name}")
    else:
        F += 1; print(f"  FAIL {name} {detail}")

print("[1] indicators + feed")
try:
    import indicators as I, feed
    cs = feed.candles("EURUSD", interval="1h", rng="10d")
    ok("candles loaded", len(cs) >= 200, f"n={len(cs)}")
    c = [x["c"] for x in cs]
    e = I.ema(c, 21); r = I.rsi(c, 14); a = I.atr(cs, 14); ax = I.adx(cs, 14)
    ok("ema len", bool(e) and len(e) == len(c))
    ok("rsi 0..100", bool(r) and 0 <= r[-1] <= 100, f"{r[-1] if r else None}")
    ok("atr>0", bool(a) and a[-1] > 0)
    ok("adx 0..100", bool(ax) and 0 <= ax[-1] <= 100)
except Exception as ex:
    ok("indicators", False, repr(ex))

print("[2] intel service (live)")
def http(path, headers=None):
    req = urllib.request.Request("http://localhost:8091" + path, headers=headers or {})
    try:
        return urllib.request.urlopen(req, timeout=15).getcode()
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0
try:
    ok("health 200", http("/health") == 200)
    ok("unpaid 402", http("/intel?symbol=EURUSD") == 402)
    ok("paid 200", http("/intel?symbol=EURUSD", {"X-PAYMENT": "0x" + "ab" * 40}) == 200)
    ok("docs 200", http("/docs") == 200)
except Exception as ex:
    ok("intel reachable", False, repr(ex))

print("[3] settlement ledger")
try:
    import settle
    r = settle.run()
    ok("settlement computes", "expected_usdc" in r)
except Exception as ex:
    ok("settlement", False, repr(ex))

print(f"\nRESULT: {P} passed, {F} failed")
sys.exit(1 if F else 0)
