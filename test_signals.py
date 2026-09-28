from fxintel.signals import build_plan
def bars(c0,n=30,up=True):
    out=[]; c=c0
    for i in range(n):
        o=c; c=c*(1.001 if up else 0.999)
        out.append({"o":o,"h":max(o,c)*1.0005,"l":min(o,c)*0.9995,"c":c,"v":1000+i*10})
    return out
# aligned LONG: uptrend + strong positive flow
plan=build_plan("EURUSD", bars(1.1000,30,True),
    {"price":1.1300,"trend":"UP","regime":"ACCUMULATION","flow_score":40,"vol_state":"expanding"},10000,1.0)
print("LONG :",plan.side,plan.valid,"stop",plan.stop,"size",plan.size_lots,"RR",plan.rr,"risk$",plan.risk_usd)
assert plan.side=="LONG" and plan.valid and plan.stop<plan.entry and plan.risk_usd<=100.01
# aligned SHORT
plan2=build_plan("EURUSD", bars(1.1300,30,False),
    {"price":1.1000,"trend":"DOWN","regime":"DISTRIBUTION","flow_score":-40,"vol_state":"expanding"},10000,1.0)
print("SHORT:",plan2.side,plan2.valid,"stop",plan2.stop,"size",plan2.size_lots,"RR",plan2.rr,"risk$",plan2.risk_usd)
assert plan2.side=="SHORT" and plan2.valid and plan2.stop>plan2.entry
# conflict -> stand aside
plan3=build_plan("EURUSD", bars(1.1000,30,True),
    {"price":1.1300,"trend":"UP","regime":"DISTRIBUTION","flow_score":-40},10000,1.0)
print("CONFLICT:",plan3.side,plan3.valid)
assert plan3.side=="FLAT" and not plan3.valid
print("ALL SIGNAL TESTS PASS")
