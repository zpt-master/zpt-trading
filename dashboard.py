"""Creator audit dashboard. Read-only HTTP server on :8088.
Serves a live HTML page + JSON API. No secrets exposed beyond what the
creator already owns (this is their own agent's state).
Endpoints: / (html)  /api/state  /api/journal  /api/risk  /api/news  /api/backtest
"""
import json, os, glob, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone

HERE=os.path.dirname(os.path.abspath(__file__))
BRIDGE="http://localhost:4790"; TOKEN=os.environ.get("MT5_TOKEN","change-me-shared-secret")
PORT=int(os.environ.get("DASH_PORT","8088"))

def jload(p, default=None):
    try: return json.load(open(p))
    except Exception: return default

def bridge(path):
    try:
        r=urllib.request.Request(BRIDGE+path,headers={"Authorization":f"Bearer {TOKEN}"})
        return json.load(urllib.request.urlopen(r,timeout=8))
    except Exception as e: return {"error":str(e)}

def api_state():
    st=bridge("/mt5/state"); return {"ts":datetime.now(timezone.utc).isoformat(),"mt5":st}

def api_journal():
    rows=[]
    for f in sorted(glob.glob(os.path.join(HERE,"logs","trades.jsonl"))):
        for line in open(f):
            try: rows.append(json.loads(line))
            except Exception: pass
    return {"trades":rows[-200:],"count":len(rows)}

def api_risk():  return jload(os.path.join(HERE,"state.json"),{})
def api_news():
    day=datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p=os.path.join(HERE,"logs",f"news-{day}.jsonl")
    items=[json.loads(l) for l in open(p)] if os.path.exists(p) else []
    return {"count":len(items),"high":[i for i in items if i.get("score",0)>=4][:20]}
def api_backtest():
    out={}
    for f in ["backtest-1y.json","backtest2-1y.json","optimizer.json"]:
        p=os.path.join(HERE,"logs",f); 
        if os.path.exists(p): out[f]=jload(p,[])
    return out

HTML="""<!doctype html><html><head><meta charset=utf-8>
<title>ZptMaster Trading</title>
<style>body{background:#0b0f14;color:#d6e2ee;font:14px/1.5 ui-monospace,Menlo,monospace;margin:0;padding:24px}
h1{color:#5cf;margin:0 0 4px}.sub{color:#789;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
.card{background:#121a22;border:1px solid #1d2a36;border-radius:10px;padding:16px}
.card h2{margin:0 0 10px;font-size:13px;color:#5cf;text-transform:uppercase;letter-spacing:.08em}
.big{font-size:26px;color:#fff}.pos{color:#4ade80}.neg{color:#f87171}.muted{color:#789}
table{width:100%;border-collapse:collapse;font-size:12px}td,th{text-align:left;padding:3px 6px;border-bottom:1px solid #1d2a36}
pre{white-space:pre-wrap;color:#9fb3c8;font-size:11px;margin:0}</style></head><body>
<h1>ZptMaster · Trading Control</h1><div class=sub id=upd>loading…</div>
<div class=grid>
<div class=card><h2>Account</h2><div id=acct></div></div>
<div class=card><h2>Risk Gates</h2><div id=risk></div></div>
<div class=card><h2>Open Positions</h2><div id=pos></div></div>
<div class=card><h2>Closed Trades (journal)</h2><div id=jrn></div></div>
<div class=card><h2>News / Event Risk</h2><div id=news></div></div>
<div class=card><h2>Strategy Backtests</h2><div id=bt></div></div>
</div>
<script>
const g=async u=>(await fetch(u)).json();
const money=x=>(x==null?'—':'$'+Number(x).toLocaleString(undefined,{maximumFractionDigits:2}));
async function tick(){
 try{
  const s=await g('/api/state'), r=await g('/api/risk'), j=await g('/api/journal'), n=await g('/api/news');
  const snap=(s.mt5&&s.mt5.snapshot)||{};
  document.getElementById('upd').textContent='updated '+new Date(s.ts).toLocaleTimeString()+'  ·  mode '+((snap.tradeMode===0)?'DEMO':'LIVE');
  const bal=snap.balance,eq=snap.equity,hw=r.high_water_balance||0;
  document.getElementById('acct').innerHTML=
    `<div class=big>${money(bal)}</div><table>
     <tr><td>Equity</td><td>${money(eq)}</td></tr>
     <tr><td>High-water</td><td>${money(hw)}</td></tr>
     <tr><td>vs HWM</td><td class=${bal>=hw?'pos':'neg'}>${bal>=hw?'ABOVE':'BELOW'}</td></tr>
     <tr><td>Server</td><td>${snap.server||'—'}</td></tr></table>`;
  document.getElementById('risk').innerHTML=
    `<table><tr><td>Risk/trade</td><td>1.0%</td></tr>
     <tr><td>Trades today</td><td>${r.trades_today??0} / 6</td></tr>
     <tr><td>Consec. losses</td><td>${r.consecutive_losses??0} / 3</td></tr>
     <tr><td>Day realized</td><td class=${(r.day_realized||0)>=0?'pos':'neg'}>${money(r.day_realized||0)}</td></tr>
     <tr><td>Halted</td><td class=${r.halted?'neg':'pos'}>${r.halted?('YES · '+(r.halt_reason||'')):'no'}</td></tr></table>`;
  const ps=(snap.positions||[]);
  document.getElementById('pos').innerHTML=ps.length?('<table><tr><th>Sym</th><th>Side</th><th>Vol</th><th>P&L</th></tr>'+
    ps.map(p=>`<tr><td>${p.symbol}</td><td>${p.type||p.side}</td><td>${p.volume}</td><td class=${(p.profit||0)>=0?'pos':'neg'}>${money(p.profit)}</td></tr>`).join('')+'</table>'):'<span class=muted>flat — no open positions</span>';
  const trs=j.trades||[];
  document.getElementById('jrn').innerHTML=trs.length?('<table><tr><th>Time</th><th>Sym</th><th>P&L</th></tr>'+
    trs.slice(-8).reverse().map(t=>`<tr><td>${(t.ts||'').slice(11,19)}</td><td>${t.symbol}</td><td class=${t.pnl>=0?'pos':'neg'}>${money(t.pnl)}</td></tr>`).join('')+'</table>'):'<span class=muted>no closed trades yet</span>';
  document.getElementById('news').innerHTML=`<div class=muted>${n.count} items scanned · ${(n.high||[]).length} high-impact</div>`+
    (n.high||[]).slice(0,5).map(h=>`<div style="font-size:12px;margin-top:6px">[${h.score}] ${h.title.slice(0,95)}</div>`).join('');
 }catch(e){document.getElementById('upd').textContent='error: '+e}
}
tick();setInterval(tick,20000);
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def _send(self,body,ctype="application/json",code=200):
        b=body.encode() if isinstance(body,str) else body
        self.send_response(code); self.send_header("Content-Type",ctype)
        self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        p=self.path.split("?")[0]
        try:
            if p=="/": return self._send(HTML,"text/html")
            if p=="/api/state": return self._send(json.dumps(api_state()))
            if p=="/api/risk": return self._send(json.dumps(api_risk()))
            if p=="/api/journal": return self._send(json.dumps(api_journal()))
            if p=="/api/news": return self._send(json.dumps(api_news()))
            if p=="/api/backtest": return self._send(json.dumps(api_backtest()))
            return self._send(json.dumps({"error":"not found"}),code=404)
        except Exception as e:
            return self._send(json.dumps({"error":str(e)}),code=500)
    def log_message(self,*a): pass

if __name__=="__main__":
    print(f"dashboard on :{PORT}")
    HTTPServer(("0.0.0.0",PORT),H).serve_forever()
