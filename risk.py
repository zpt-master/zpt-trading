"""Risk manager — genesis rules enforced in code."""
import json, os, time
from specs import value_per_price_unit

STATE = os.path.join(os.path.dirname(__file__), "state.json")
DEFAULTS = {
    "high_water_balance": 0.0, "day": "", "day_start_balance": 0.0,
    "day_realized": 0.0, "trades_today": 0, "consecutive_losses": 0,
    "halted": False, "halt_reason": "", "last_order_id": None,
}
MAX_RISK_PCT       = 0.01
MAX_TRADES_PER_DAY = 6
MAX_CONSEC_LOSSES  = 3
DAILY_LOSS_CAP_PCT = 0.03
MAX_OPEN_POSITIONS = 3

def load():
    return {**DEFAULTS, **json.load(open(STATE))} if os.path.exists(STATE) else dict(DEFAULTS)

def save(s):
    tmp = STATE + ".tmp"; json.dump(s, open(tmp, "w"), indent=2); os.replace(tmp, STATE)

def check_day(s, balance):
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if s["day"] != today:
        s["day"] = today
        s["day_start_balance"] = s["high_water_balance"] or balance
        s["day_realized"] = 0.0
        s["trades_today"] = 0
    if balance > s["high_water_balance"]:
        s["high_water_balance"] = balance
    return s

def can_open(s, equity, open_positions):
    if s["halted"]:                    return False, f"halted: {s['halt_reason']}"
    if open_positions >= MAX_OPEN_POSITIONS: return False, f"max open positions ({MAX_OPEN_POSITIONS})"
    if s["trades_today"] >= MAX_TRADES_PER_DAY: return False, f"max trades/day ({MAX_TRADES_PER_DAY})"
    if s["consecutive_losses"] >= MAX_CONSEC_LOSSES: return False, "consecutive-loss cooldown"
    pct = (s["day_realized"] / s["day_start_balance"]) if s["day_start_balance"] else 0
    if pct <= -DAILY_LOSS_CAP_PCT:     return False, f"daily loss cap ({pct:.2%})"
    return True, "ok"

def position_size(equity, symbol, sl_distance, price=None, max_lots=20.0):
    if sl_distance <= 0: return 0.0
    vpu = value_per_price_unit(symbol, price)
    loss_at_1lot = sl_distance * vpu
    if loss_at_1lot <= 0: return 0.0
    lots = (equity * MAX_RISK_PCT) / loss_at_1lot
    return round(max(0.01, min(lots, max_lots)), 2)

def record_result(s, filled, real_sl_price=None):
    if filled: s["trades_today"] += 1
