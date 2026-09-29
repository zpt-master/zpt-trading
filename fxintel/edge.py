"""Edge gate - statistical justification before any live order.

Genesis law: never gamble the creator's capital. An order may only be placed
when a strategy shows positive expectancy AFTER costs on the symbol's own
history, judged on a held-out (most recent) out-of-sample slice. Fails closed:
no edge -> approved=False -> the trader places no order.

Candidates: trend (EMA20/50 + ADX>=adx_min), revert (RSI<30 / >70),
breakout (Donchian 20). Indicators come from fxintel.indicators, which return
lists aligned to the input series.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List
from .indicators import ema, rsi, atr, adx


@dataclass
class EdgeReport:
    symbol: str
    strategy: str
    trades: int
    win_rate: float
    avg_win_R: float
    avg_loss_R: float
    expectancy_R: float
    profit_factor: float
    approved: bool
    reason: str

    def to_dict(self):
        return asdict(self)



def _K(b, *names):
    """Fetch the first present key from a bar (dict or obj).
    Accepts _K(b, "close", "c") or _K(b, ("close", "c"))."""
    flat = []
    for n in names:
        if isinstance(n, (list, tuple)):
            flat.extend(n)
        else:
            flat.append(n)
    for n in flat:
        if isinstance(b, dict):
            if n in b and b[n] is not None:
                return float(b[n])
        else:
            v = getattr(b, n, None)
            if v is not None:
                return float(v)
    raise KeyError(flat[0] if flat else "key")
def _norm(bars):
    """Normalize OHLC keys to {'o','h','l','c'} for indicators.py."""
    out = []
    for b in bars:
        out.append({
            "o": float(b.get("open", b.get("o"))),
            "h": float(b.get("high", b.get("h"))),
            "l": float(b.get("low", b.get("l"))),
            "c": float(b.get("close", b.get("c"))),
            "time": b.get("time", b.get("t")),
        })
    return out


def _stats(trades):
    if not trades:
        return 0, 0.0, 0.0, 0.0, 0.0, 0.0
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    wr = len(wins) / len(trades)
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    exp = sum(trades) / len(trades)
    gw = sum(wins)
    gl = abs(sum(losses))
    pf = (gw / gl) if gl > 0 else (float("inf") if gw > 0 else 0.0)
    return len(trades), wr, aw, al, exp, pf


def _simulate(bars, atr_s, signals, rr=1.5, cost_R=0.10, max_hold=60):
    """R-multiple outcomes. 1R = 1*ATR; target = rr*ATR. Cost subtracted."""
    trades = []
    n = len(bars)
    for idx, direction in signals:
        if idx + 1 >= n:
            continue
        a = atr_s[idx]
        if not a or a <= 0:
            continue
        entry = _K(bars[idx], ("close","c"))
        stop = entry - a if direction > 0 else entry + a
        target = entry + rr * a if direction > 0 else entry - rr * a
        outcome = None
        for j in range(idx + 1, min(idx + 1 + max_hold, n)):
            hi, lo = _K(bars[j], "high", "h"), _K(bars[j], "low", "l")
            if direction > 0:
                if lo <= stop:
                    outcome = -1.0
                    break
                if hi >= target:
                    outcome = float(rr)
                    break
            else:
                if hi >= stop:
                    outcome = -1.0
                    break
                if lo <= target:
                    outcome = float(rr)
                    break
        if outcome is None:
            j = min(idx + max_hold, n - 1)
            move = (_K(bars[j], "close", "c") - entry) * direction
            outcome = max(-1.0, min(float(rr), move / a))
        trades.append(outcome - cost_R)
    return trades


def _signals_trend(closes, fast, slow, adx_s, adx_min):
    sig = []
    for i in range(len(closes)):
        f, s, a = fast[i], slow[i], adx_s[i]
        if f is None or s is None or a is None or a < adx_min:
            continue
        if f > s:
            sig.append((i, 1))
        elif f < s:
            sig.append((i, -1))
    return sig


def _signals_revert(rsi_s, lo=30.0, hi=70.0):
    sig = []
    for i in range(len(rsi_s)):
        r = rsi_s[i]
        if r is None:
            continue
        if r < lo:
            sig.append((i, 1))
        elif r > hi:
            sig.append((i, -1))
    return sig


def _signals_breakout(bars, s_atr, lookback=20, atr_mult=1.0):
    """Breakout with ATR buffer to avoid noise-breakouts on 1-bar spikes."""
    sig = []
    closes = [_K(b, "close", "c") for b in bars]
    for i in range(lookback, len(bars)):
        a = s_atr[i]
        if not a:
            continue
        w = bars[i - lookback:i]
        dmax = max(_K(b, "high", "h") for b in w)
        dmin = min(_K(b, "low", "l") for b in w)
        if closes[i] > dmax + atr_mult * a * 0.25:
            sig.append((i, 1))
        elif closes[i] < dmin - atr_mult * a * 0.25:
            sig.append((i, -1))
    return sig


def evaluate(symbol, bars, rr=1.5, cost_R=0.10, adx_min=20.0, oos_frac=0.35,
             min_trades=8, min_expectancy_R=0.03, min_profit_factor=1.10):
    if len(bars) < 120:
        return [EdgeReport(symbol, "insufficient_data", 0, 0, 0, 0, 0, 0, False,
                           "need >=120 bars, have %d" % len(bars))]

    closes = [_K(b, "close", "c") for b in bars]
    nb = _norm(bars)
    s_atr = atr(nb, 14)           # aligned list
    fast = ema(closes, 20)
    slow = ema(closes, 50)
    rsi_s = rsi(closes, 14)
    adx_s = adx(nb, 14)           # aligned list

    # Only judge on the most recent out-of-sample slice.
    split = int(len(bars) * (1 - oos_frac))
    reports = []

    def _eval(name, signals):
        oos = [(i, d) for (i, d) in signals if i >= split]
        trades = _simulate(bars, s_atr, oos, rr=rr, cost_R=cost_R)
        n, wr, aw, al, exp, pf = _stats(trades)
        ok = (n >= min_trades and exp >= min_expectancy_R and pf >= min_profit_factor)
        if ok:
            reason = "approved: positive OOS expectancy after costs"
        elif n < min_trades:
            reason = "reject: only %d OOS trades (< %d)" % (n, min_trades)
        elif exp < min_expectancy_R:
            reason = "reject: OOS expectancy %.3fR < %.2fR" % (exp, min_expectancy_R)
        else:
            reason = "reject: OOS profit factor %.2f < %.2f" % (pf, min_profit_factor)
        reports.append(EdgeReport(symbol, name, n, round(wr, 4), round(aw, 3),
                                  round(al, 3), round(exp, 4),
                                  (round(pf, 3) if pf != float("inf") else 999.0),
                                  ok, reason))

    _eval("trend", _signals_trend(closes, fast, slow, adx_s, adx_min))
    _eval("revert", _signals_revert(rsi_s))
    _eval("breakout", _signals_breakout(bars, s_atr, 20))
    return reports


def best(symbol, bars, **kw):
    reports = evaluate(symbol, bars, **kw)
    ok = [r for r in reports if r.approved]
    if ok:
        return max(ok, key=lambda r: r.expectancy_R)
    return max(reports, key=lambda r: r.expectancy_R)
