"""Risk manager — the hard rules from the genesis prompt, enforced in code."""
import json, os, time

STATE = os.path.join(os.path.dirname(__file__), "state.json")

DEFAULTS = {
    "high_water_balance": 0.0,      # creator's rule: baseline = highest balance
    "day": "",                      # UTC date of current ledger
    "day_start_balance": 0.0,
    "day_realized": 0.0,
    "trades_today": 0,
    "consecutive_losses": 0,
    "halted": False,
    "halt_reason": "",
}

def load():
    if os.path.exists(STATE):
        d = json.load(open(STATE))
        return {**DEFAULTS, **d}
    return dict(DEFAULTS)

def save(s):
    tmp = STATE + ".tmp"
    json.dump(s, open(tmp, "w"), indent=2)
    os.replace(tmp, STATE)

# --- hard limits (do not loosen without creator approval) ---
MAX_RISK_PCT        = 0.01    # 1% of equity at risk per trade
MAX_TRADES_PER_DAY  = 6
MAX_CONSEC_LOSSES   = 3       # then pause 24h
DAILY_LOSS_CAP_PCT  = 0.03    # -3% day -> stop for the day
MAX_OPEN_POSITIONS  = 3

def check_day(s, balance):
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if s["day"] != today:
        s["day"] = today
        s["day_start_balance"] = balance
        s["day_realized"] = 0.0
        s["trades_today"] = 0
        # do NOT auto-clear consecutive_losses; that resets on a win
    if balance > s["high_water_balance"]:
        s["high_water_balance"] = balance
    return s

def can_open(s, equity, open_positions):
    if s["halted"]:
        return False, f"halted: {s['halt_reason']}"
    if open_positions >= MAX_OPEN_POSITIONS:
        return False, f"max open positions ({MAX_OPEN_POSITIONS})"
    if s["trades_today"] >= MAX_TRADES_PER_DAY:
        return False, f"max trades/day ({MAX_TRADES_PER_DAY})"
    if s["consecutive_losses"] >= MAX_CONSEC_LOSSES:
        return False, f"consecutive losses ({s['consecutive_losses']}) - cooldown"
    day_pnl_pct = (s["day_realized"] / s["day_start_balance"]) if s["day_start_balance"] else 0
    if day_pnl_pct <= -DAILY_LOSS_CAP_PCT:
        return False, f"daily loss cap hit ({day_pnl_pct:.2%})"
    return True, "ok"

def position_size(equity, sl_distance, pip_value_per_lot=10.0, pip=0.0001):
    """Lots such that a stop-out loses MAX_RISK_PCT of equity.
    pip_value_per_lot: USD per pip per 1.00 lot (10.0 for EURUSD-like)."""
    risk_usd = equity * MAX_RISK_PCT
    sl_pips = sl_distance / pip
    if sl_pips <= 0: return 0.0
    lots = risk_usd / (sl_pips * pip_value_per_lot)
    return round(max(0.01, min(lots, 5.0)), 2)  # clamp; bridge enforces its own cap
