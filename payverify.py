"""
payverify.py - real x402 payment verification for Conway Intelligence.
Replaces the len>20 header stub with on-chain verification: an X-PAYMENT
proof must carry a Base tx hash whose receipt shows a confirmed USDC
Transfer of >= the required amount to PAY_TO. Dependency-free. Fail-closed.
"""
import json, base64, re, urllib.request

RPC_URLS = ["https://mainnet.base.org","https://base-rpc.publicnode.com","https://base.drpc.org","https://1rpc.io/base"]
USDC_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

def _rpc(method, params, timeout=12):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    last=None
    for url in RPC_URLS:
        try:
            req=urllib.request.Request(url,data=body,headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0 (compatible; ConwayIntel/1.0)"})
            with urllib.request.urlopen(req,timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last=e
    raise RuntimeError("all RPCs failed: %s"%last)

def _extract_txhash(proof):
    if not proof: return None
    p=proof.strip()
    if p.startswith("0x") and len(p)==66: return p
    dec=p
    try:
        dec=base64.b64decode(p + "="*(-len(p)%4)).decode("utf-8","ignore")
    except Exception:
        dec=p
    try:
        obj=json.loads(dec)
    except Exception:
        m=re.search(r"0x[0-9a-fA-F]{64}", dec); return m.group(0) if m else None
    def scan(o):
        if isinstance(o,dict):
            for k in ("txHash","tx_hash","hash","transactionHash"):
                v=o.get(k)
                if isinstance(v,str) and v.startswith("0x") and len(v)==66: return v
            for k in ("payload","transaction","proof","payment"):
                r=scan(o.get(k))
                if r: return r
        elif isinstance(o,str) and o.startswith("0x") and len(o)==66:
            return o
        return None
    return scan(obj)

def verify_payment(proof, pay_to, amount_usdc):
    detail={"verified":False}
    txh=_extract_txhash(proof)
    if not txh:
        detail["reason"]="no tx hash found in proof"; return False, detail
    detail["txHash"]=txh
    try:
        res=_rpc("eth_getTransactionReceipt",[txh]).get("result")
    except Exception as e:
        detail["reason"]="rpc error: %s"%e; return False, detail
    if not res:
        detail["reason"]="tx not found / not mined"; return False, detail
    if res.get("status") not in ("0x1",1):
        detail["reason"]="tx failed status=%s"%res.get("status"); return False, detail
    want=int(round(float(amount_usdc)*1000000)); total=0
    for lg in res.get("logs",[]):
        if lg.get("address","").lower()!=USDC_BASE: continue
        t=lg.get("topics",[])
        if not t or t[0].lower()!=TRANSFER_TOPIC: continue
        to="0x"+t[2][-40:]
        val=int(lg.get("data","0x0") or "0x0",16) if lg.get("data") not in (None,"0x") else 0
        if to.lower()==pay_to.lower(): total+=val
    detail["usdc_received_units"]=total; detail["block"]=res.get("blockNumber")
    if total<want:
        detail["reason"]="insufficient: %d < %d units"%(total,want); return False, detail
    detail["verified"]=True; detail["reason"]="confirmed USDC transfer to payTo"; return True, detail

if __name__=="__main__":
    import sys
    proof=sys.argv[1] if len(sys.argv)>1 else ""
    to=sys.argv[2] if len(sys.argv)>2 else "0x0190fa69E9e2731fC32Ef6f02B66955dF16B0E5D"
    amt=float(sys.argv[3]) if len(sys.argv)>3 else 0.02
    ok,det=verify_payment(proof,to,amt)
    print(json.dumps({"ok":ok,"detail":det},indent=2))
