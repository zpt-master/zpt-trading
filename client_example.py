"""Reference client for Conway Intelligence.
Shows how a buyer pays per call via x402 (USDC on Base) and consumes signal.
Usage:  python3 client_example.py EURUSD --url http://HOST:8091
"""
import json, sys, urllib.request, os
def get_intel(symbol, base):
    # 1) ask without payment -> server replies 402 with payment requirements
    req=urllib.request.Request(f"{base}/intel?symbol={symbol}")
    try:
        return json.load(urllib.request.urlopen(req, timeout=15))
    except urllib.error.HTTPError as e:
        if e.code!=402: raise
        terms=json.load(e)
        acc=terms["accepts"][0]
        print(f"# payment required: {acc['maxAmountRequired']} {acc['asset']} -> {acc['payTo']} ({acc['network']})")
        # 2) in production: sign a USDC transfer with your wallet and set X-PAYMENT.
        proof=os.environ.get("X402_PROOF","")
        if not proof:
            print("# set X402_PROOF=<signed payment> to consume. (Demo stops here.)")
            return None
        req2=urllib.request.Request(f"{base}/intel?symbol={symbol}", headers={"X-PAYMENT":proof})
        return json.load(urllib.request.urlopen(req2, timeout=15))
if __name__=="__main__":
    sym=sys.argv[1] if len(sys.argv)>1 else "EURUSD"
    base=sys.argv[sys.argv.index("--url")+1] if "--url" in sys.argv else "http://localhost:8091"
    r=get_intel(sym, base)
    print(json.dumps(r, indent=2) if r else "")
