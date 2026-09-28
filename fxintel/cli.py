"""CLI: python3 -m fxintel.cli SYMBOL [SYMBOL...]"""
import sys, json
from .summary import summarize
def main(argv):
    try:
        import feed
    except ImportError:
        print("feed module required for live data", file=sys.stderr); return 2
    syms = argv[1:] or ["EURUSD","GBPUSD","USDJPY","XAUUSD"]
    out=[]
    for s in syms:
        try:
            cs = feed.candles(s, interval="1h", rng="10d")
            out.append(summarize(s, cs, account_equity=10000))
        except Exception as e:
            out.append({"symbol":s,"error":repr(e)})
    print(json.dumps(out, indent=2))
    return 0
if __name__=="__main__":
    sys.exit(main(sys.argv))
