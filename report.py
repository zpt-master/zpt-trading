"""Daily settlement report (runs before 08:00 GMT+7 = 01:00 UTC).
Implements the creator's ledger: baseline = high-water balance; if today's
balance <= high-water, the day counts as a LOSS regardless of nominal gain."""
import json, os, time, urllib.request
from datetime import datetime, timezone

BRIDGE="http://localhost:4790"; TOKEN=os.environ.get("MT5_TOKEN","change-me-shared-secret")
STATE=os.path.join(os.path.dirname(__file__),"state.json")

def bridge(p):
    r=urllib.request.Request(BRIDGE+p,headers={"Authorization":f"Bearer {TOKEN}"})
    return json.load(urllib.request.urlopen(r,timeout=12))

s=json.load(open(STATE)) if os.path.exists(STATE) else {}
st=bridge("/mt5/state")["snapshot"]
bal=st["balance"]; hw=max(s.get("high_water_balance",0 or 0), bal)
day_start=s.get("day_start_balance",bal)
delta=bal-day_start
verdict="WIN" if bal>s.get("high_water_balance",0) else "LOSS"
lines=[
 f"# Trading Report {datetime.now(timezone.utc).date().isoformat()} (UTC)",
 f"Mode: {'DEMO' if st.get('tradeMode')==0 else 'LIVE'}",
 f"Balance: ${bal:,.2f}",
 f"Day start: ${day_start:,.2f}",
 f"Day P&L: ${delta:+,.2f}",
 f"High-water: ${hw:,.2f}",
 f"Trades today: {s.get('trades_today',0)}",
 f"Consecutive losses: {s.get('consecutive_losses',0)}",
 f"Halted: {s.get('halted',False)} {s.get('halt_reason','')}",
 f"Verdict vs high-water: {verdict}",
 f"Credits to add 1:1: ${max(0,delta):,.2f}" if verdict=="WIN" else "Credits to add 1:1: $0.00",
]
open(os.path.join(os.path.dirname(__file__),"logs",f"report-{time.strftime('%Y-%m-%d')}.md"),"w").write("\n".join(lines)+"\n")
print("\n".join(lines))
