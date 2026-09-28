#!/usr/bin/env python3
"""Live validation of payverify.py against REAL Base USDC transfers.
Proves the money path is real: a genuine buyer's USDC transfer to payTo is
confirmed, and a fake proof / wrong recipient is rejected. Public RPC only."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import payverify
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
OUR = "0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D"

def find_recent_transfer():
    head = int(payverify._rpc("eth_blockNumber", [])["result"], 16)
    for depth in range(0, 60):
        blk = payverify._rpc("eth_getBlockByNumber", [hex(head-depth), True]).get("result")
        if not blk: continue
        for tx in blk.get("transactions", []):
            h = tx.get("hash")
            rc = payverify._rpc("eth_getTransactionReceipt", [h]).get("result")
            if not rc or rc.get("status") not in ("0x1", 1): continue
            for lg in rc.get("logs", []):
                if lg.get("address","").lower() != USDC.lower(): continue
                t = lg.get("topics", [])
                if not t or t[0].lower() != payverify.TRANSFER_TOPIC: continue
                to = "0x" + t[2][-40:]
                data = lg.get("data","0x0") or "0x0"
                units = int(data,16) if data not in ("0x","") else 0
                if units > 0: return h, to, units
        if depth > 25: break
    return None, None, None

def main():
    print("== TEST 1: reject garbage proof (fail-closed) ==")
    ok, det = payverify.verify_payment("not-a-real-proof", OUR, 0.02)
    assert ok is False; print("  PASS rejected:", det.get("reason"))
    print("== TEST 2: real on-chain USDC transfer is confirmed ==")
    txh, to, units = find_recent_transfer()
    if not txh:
        print("  SKIP: no recent USDC transfer found"); return 0
    amt = units/1_000_000
    print(f"  sampled tx={txh[:18]}... to={to} amount={amt} USDC")
    ok, det = payverify.verify_payment(txh, to, max(0.000001, amt*0.5))
    assert ok is True, f"real transfer should verify: {det}"
    print("  PASS verified:", det.get("reason"), "units=", det.get("usdc_received_units"))
    print("== TEST 3: real transfer to the WRONG recipient is rejected ==")
    ok, det = payverify.verify_payment(txh, OUR, 0.000001)
    print("  result:", ok, det.get("reason"))
    if to.lower() != OUR.lower():
        assert ok is False; print("  PASS correctly rejected (wrong recipient)")
    print("\nALL LIVE PAYVERIFY TESTS PASSED"); return 0

if __name__ == "__main__":
    sys.exit(main())
