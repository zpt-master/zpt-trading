"""Contract specs: USD P&L per 1.0 price-unit move per 1.0 lot."""
def value_per_price_unit(symbol, price=None):
    s = symbol.upper().replace("+", "")
    if s in ("EURUSD","GBPUSD","AUDUSD","NZDUSD","EURGBP","EURCHF","AUDNZD","EURAUD","GBPAUD","GBPCHF","EURJPY","GBPJPY","CHFJPY","AUDJPY","CADJPY","NZDJPY"):
        if s.endswith("JPY"):
            # XXXJPY 1 lot = 100,000 base; P&L in JPY -> USD ; needs price
            return 100000.0 / (price or 150.0)
        return 100000.0
    if s in ("USDJPY","USDCHF","USDCAD"):
        return 100000.0 / (price or 1.0) if s == "USDJPY" else 100000.0 / (price or 1.0)
    if s == "XAUUSD":  return 100.0      # 100 oz/lot
    if s == "XAGUSD":  return 5000.0     # 5000 oz/lot
    return 100000.0
