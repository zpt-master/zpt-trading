"""Conway Intelligence — sellable market-intelligence API (x402-gated).
Sells COMPUTED intelligence: regime, trend, volatility state, key levels,
event-risk, plain-language summary. Zero third-party deps.
Endpoints: GET /intel?symbol=EURUSD&tf=1h  (paid) | GET /health (free)
"""
import json, os, sys, time, urllib.parse
import payverify
from fxintel import moneyflow
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
# config.json is the source of truth (so watchdogs work without env vars)
try:
    _cfg=json.load(open(os.path.join(HERE,"config.json")))
    os.environ.setdefault("X402_PAY_TO", _cfg["x402"]["pay_to"] if _cfg["x402"].get("enabled") else "")
    os.environ.setdefault("INTEL_PRICE_USDC", str(_cfg["x402"]["intel_price_usdc"]))
except Exception: pass
import feed
from indicators import ema, rsi, atr, adx

PORT=int(os.environ.get("INTEL_PORT","8091"))
PRICE_USDC=os.environ.get("INTEL_PRICE_USDC","0.02")
PAY_TO=os.environ.get("X402_PAY_TO","")
NETWORK=os.environ.get("X402_NETWORK","base")
CACHE_TTL=int(os.environ.get("INTEL_CACHE_TTL","120"))
_cache={}
_hits={}
FREE_PER_MIN=20
SYMBOLS=["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","NZDUSD","EURJPY","GBPJPY","AUDJPY","XAUUSD"]

def event_risk():
    p=os.path.join(HERE,"pause_news.flag")
    if not os.path.exists(p): return {"active":False}
    try:
        d=json.load(open(p))
        if time.time()>=d.get("expires",0): return {"active":False}
        return {"active":True,"reason":d.get("reason","")[:120]}
    except Exception: return {"active":False}

def pctile(series,v):
    if not series: return None
    return round(100*sum(1 for x in series if x<=v)/len(series))

def intel(symbol,tf="1h"):
    key=f"{symbol}:{tf}"; now=time.time()
    if key in _cache and now-_cache[key][0]<CACHE_TTL: return _cache[key][1]
    cs=feed.candles(symbol,interval=tf,rng="10d" if tf=="1h" else "60d")
    if len(cs)<220: return {"symbol":symbol,"error":f"insufficient data ({len(cs)} bars)"}
    closes=[c["c"] for c in cs]
    ef,es,et=ema(closes,21),ema(closes,55),ema(closes,200)
    r=rsi(closes,14); a=atr(cs,14); ax=adx(cs,14)
    price=closes[-1]; a_now=a[-1] if a else 0.0
    atr_hist=a[-200:] if len(a)>=200 else a
    swing_hi=max(x["h"] for x in cs[-50:]); swing_lo=min(x["l"] for x in cs[-50:])
    trend="range"
    if ef and es and et:
        if ef[-1]>es[-1] and price>et[-1]: trend="up"
        elif ef[-1]<es[-1] and price<et[-1]: trend="down"
    strength=round(ax[-1],1) if ax else None
    regime="trending" if (strength and strength>=25) else "ranging"
    vol_pct=pctile(atr_hist,a_now) if atr_hist else None
    vol_state=("high" if (vol_pct or 0)>=70 else "low" if (vol_pct or 100)<=30 else "normal")
    bits=[]
    if regime=="trending" and trend in ("up","down"):
        bits.append(f"{symbol} is in a {trend}-trend ({regime}, ADX {strength}).")
        bits.append("Favor pullback entries WITH the trend; avoid counter-trend fades.")
    elif regime=="ranging":
        bits.append(f"{symbol} is ranging (ADX {strength}); fade extremes, expect mean-reversion.")
    bits.append(f"Volatility is {vol_state}"+(f" (ATR {a_now:.5f}, {vol_pct}th pctile)." if vol_pct is not None else "."))
    bits.append(f"Key levels: resistance {swing_hi:.5f}, support {swing_lo:.5f}.")
    ev=event_risk()
    if ev["active"]: bits.append(f"EVENT RISK ACTIVE — {ev['reason']}. Avoid new entries.")
    if r: bits.append(f"RSI(14) = {r[-1]:.1f}.")
    mf=moneyflow.analyze(cs)
    if mf.get("flow_score"):
        bits.append(f"MONEY FLOW: {mf['flow_regime']} (score {mf['flow_score']}, MFI {mf['mfi']}, RVOL {mf['rvol']}). {mf['read']}")
    out={"symbol":symbol,"tf":tf,"ts":datetime.now(timezone.utc).isoformat(),"price":round(price,5),
         "trend":trend,"regime":regime,"adx":strength,"rsi":round(r[-1],1) if r else None,
         "atr":round(a_now,6),"atr_percentile":vol_pct,"vol_state":vol_state,
         "resistance":round(swing_hi,5),"support":round(swing_lo,5),"event_risk":ev,
         "money_flow":mf,
         "summary":" ".join(bits),
         "quality_note":"Computed intelligence, not investment advice. No guaranteed edge."}
    _cache[key]=(now,out); return out

class H(BaseHTTPRequestHandler):
    def _send(self,body,ctype="application/json",code=200,extra=None):
        b=body.encode() if isinstance(body,str) else body
        self.send_response(code); self.send_header("Content-Type",ctype)
        self.send_header("Content-Length",str(len(b)))
        for k,v in (extra or {}).items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u=urllib.parse.urlparse(self.path)
        if u.path=="/product":
            f=os.path.join(HERE,"product.json")
            return self._send(open(f).read() if os.path.exists(f) else "{}")
        if u.path=="/preview":
            q=urllib.parse.parse_qs(u.query)
            sym=(q.get("symbol",["EURUSD"])[0]).upper().replace("+","")
            ip=self.client_address[0]; now=time.time()
            window=[t for t in _hits.get(ip,[]) if now-t<60]
            if len(window)>=FREE_PER_MIN:
                return self._send(json.dumps({"error":"free-tier rate limit","retry_after_s":60-int(now-window[0])}),code=429)
            window.append(now); _hits[ip]=window
            if sym not in SYMBOLS: return self._send(json.dumps({"error":"unknown symbol"}),code=400)
            d=intel(sym,"1h")
            prev={"symbol":sym,"trend":d.get("trend"),"regime":d.get("regime"),
                  "price":d.get("price"),"vol_state":d.get("vol_state"),
                  "teaser":f"{sym}: {d.get('trend')} / {d.get('regime')}. Full signal (levels, ADX, RSI, event-risk, summary) available.",
                  "upgrade":{"price_usdc":PRICE_USDC,"endpoint":f"/intel?symbol={sym}","pay_to":PAY_TO,"network":NETWORK},
                  "disclosure":"Computed intelligence, not advice. No guaranteed edge."}
            return self._send(json.dumps(prev,indent=2))
        if u.path=="/health":
            return self._send(json.dumps({"ok":True,"paid":bool(PAY_TO),"price_usdc":PRICE_USDC,"symbols":SYMBOLS}))
        if u.path in ("/docs","/intel/docs"):
            d=os.path.join(HERE,"docs.html")
            return self._send(open(d).read() if os.path.exists(d) else "docs missing","text/html")
        if u.path in ("/","/index.html"):
            f=os.path.join(HERE,"storefront.html")
            return self._send(open(f).read() if os.path.exists(f) else "Conway Intelligence API — see /docs","text/html")
        if u.path!="/intel":
            return self._send(json.dumps({"error":"not found"}),code=404)
        if PAY_TO and not self._has_payment():
            return self._send(json.dumps({"error":"payment required","x402Version":1,
                "accepts":[{"scheme":"exact","network":NETWORK,"asset":"USDC","payTo":PAY_TO,
                            "maxAmountRequired":PRICE_USDC,"resource":self.path,
                            "description":"Conway Intelligence — computed FX market intelligence"}]}),
                code=402,extra={"WWW-Authenticate":"x402"})
        q=urllib.parse.parse_qs(u.query)
        sym=(q.get("symbol",["EURUSD"])[0]).upper().replace("+","")
        tf=q.get("tf",["1h"])[0]
        if sym not in SYMBOLS:
            return self._send(json.dumps({"error":f"unknown symbol; use one of {SYMBOLS}"}),code=400)
        try: return self._send(json.dumps(intel(sym,tf),indent=2))
        except Exception as e: return self._send(json.dumps({"error":str(e)}),code=500)
    def _has_payment(self):
        proof=None
        for h in ("X-PAYMENT","X-Payment","Authorization"):
            v=self.headers.get(h)
            if v: proof=v; break
        if not proof: return False
        try:
            ok,det=payverify.verify_payment(proof,PAY_TO,PRICE_USDC)
        except Exception as e:
            ok,det=False,{"reason":"verifier error: %s"%e}
        try:
            os.makedirs(os.path.join(HERE,"logs"),exist_ok=True)
            open(os.path.join(HERE,"logs","intel_payments.jsonl"),"a").write(
                json.dumps({"ts":datetime.now(timezone.utc).isoformat(),"path":self.path,
                            "verified":ok,"detail":det})+"\n")
        except Exception: pass
        return ok
    def log_message(self,*a): pass

if __name__=="__main__":
    print(f"Conway Intelligence on :{PORT}  paid={bool(PAY_TO)}  price={PRICE_USDC} USDC")
    HTTPServer(("0.0.0.0",PORT),H).serve_forever()
