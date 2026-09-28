import sys; sys.path.insert(0,'/home/oroth/trading')
import feed, strategy2, json

def run(symbol, interval="1h", rng="1y", rr=1.5, warmup=260):
    cs=feed.candles(symbol, interval=interval, rng=rng)
    if len(cs)<warmup+10: return {"symbol":symbol,"error":f"only {len(cs)}"}
    trades=[]
    for i in range(warmup,len(cs)):
        sig=strategy2.signal(cs[:i+1])
        if not sig: continue
        entry=sig["price"]; d=sig["sl_dist"]
        sl,tp=(entry-d,entry+d*rr) if sig["side"]=="buy" else (entry+d,entry-d*rr)
        for j in range(i+1,min(i+200,len(cs))):
            h,l=cs[j]["h"],cs[j]["l"]
            if sig["side"]=="buy":
                if l<=sl: trades.append(-1.0); break
                if h>=tp: trades.append(rr); break
            else:
                if h>=sl: trades.append(-1.0); break
                if l<=tp: trades.append(rr); break
    if not trades: return {"symbol":symbol,"interval":interval,"trades":0}
    eq=1.0;peak=1.0;mdd=0.0
    for R in trades:
        eq*=(1+0.01*R); peak=max(peak,eq); mdd=min(mdd,eq/peak-1)
    return {"symbol":symbol,"interval":interval,"range":rng,"trades":len(trades),
            "win_rate":round(sum(1 for x in trades if x>0)/len(trades),3),
            "avg_R":round(sum(trades)/len(trades),3),
            "return_pct_1risk":round((eq-1)*100,2),"max_dd_pct":round(mdd*100,2)}

if __name__=="__main__":
    out=[]
    for s in ["EURUSD","GBPUSD","USDJPY","AUDUSD","XAUUSD"]:
        try: out.append(run(s,"1h","1y"))
        except Exception as e: out.append({"symbol":s,"error":str(e)})
    json.dump(out,open('/home/oroth/trading/logs/backtest2-1y.json','w'),indent=2)
    print(f"{'SYM':8}{'T':>5}{'WR':>8}{'avgR':>9}{'ret%':>10}{'maxDD%':>9}")
    for r in out:
        if 'error' in r: print(f"{r['symbol']:8}{'ERR':>5} {r['error'][:30]}"); continue
        print(f"{r['symbol']:8}{r['trades']:>5}{r['win_rate']:>8}{r['avg_R']:>9}{r['return_pct_1risk']:>10}{r['max_dd_pct']:>9}")
