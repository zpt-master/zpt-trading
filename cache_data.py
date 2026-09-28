import sys, json, os; sys.path.insert(0,'/home/oroth/trading')
import feed
os.makedirs('cache',exist_ok=True)
SYMS=["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","XAUUSD","NZDUSD","EURJPY","GBPJPY","AUDJPY"]
for s in SYMS:
    for itv,rng in [("1h","2y"),("4h","4y"),("1d","10y")]:
        f=f"cache/{s}_{itv}.json"
        if os.path.exists(f): continue
        try:
            cs=feed.candles(s,interval=itv,rng=rng)
            json.dump(cs,open(f,'w'))
            print(f"cached {s} {itv} {len(cs)}")
        except Exception as e:
            print(f"FAIL {s} {itv}: {e}")
print("DONE")
