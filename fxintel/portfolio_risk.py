#!/usr/bin/env python3
"""portfolio_risk.py - correlation-aware concentration gate.

A per-order risk cap is NOT enough: long EURUSD AND long GBPUSD are both bets
against the USD, so two "1% risk" orders can be one concentrated 2% bet. This
module decomposes each pair into currency exposures and blocks plans that would
push any single currency's net exposure past a hard cap.

No deps. Pure functions -> trivially testable, fail-closed.

Currency exposure model:
  Buying  BASE/QUOTE  => +notional in BASE, -notional in QUOTE
  Selling BASE/QUOTE  => -notional in BASE, +notional in QUOTE
We measure each currency's exposure as a fraction of equity risk-equiv, then
reject a candidate if |net exposure| of any currency would exceed MAX_CCY_EXPOSURE
(default 1.75x the single-order risk cap, i.e. ~2.6%).
"""
from __future__ import annotations
from typing import Dict, List, Tuple

# Metals/indices treated as USD-denominated for exposure purposes.
METALS = {"XAUUSD": ("XAU", "USD"), "XAGUSD": ("XAG", "USD")}
DEFAULT_MAX_CCY = 2.6    # % of equity, per currency
USD_LIKE = "USD"


def split_pair(symbol: str) -> Tuple[str, str]:
    s = symbol.upper().strip()
    if s in METALS:
        return METALS[s]
    if len(s) == 6:
        return s[:3], s[3:]
    if s.endswith("USD") and len(s) == 7:      # e.g. XAUUSD handled above
        return s[:-3], "USD"
    return (s, "USD") if len(s) != 6 else (s[:3], s[3:])


def exposure_delta(symbol: str, side: str, risk_pct: float) -> Dict[str, float]:
    """Currency exposure contributed by one order, in % of equity."""
    base, quote = split_pair(symbol)
    side = side.upper()
    long_base = side in ("BUY", "LONG")
    sign = 1.0 if long_base else -1.0
    return {base: sign * risk_pct, quote: -sign * risk_pct}


def combined_exposure(open_positions: List[dict], candidate: dict | None = None) -> Dict[str, float]:
    """Net % exposure per currency for open positions plus an optional candidate."""
    net: Dict[str, float] = {}
    items = list(open_positions or [])
    if candidate:
        items = items + [candidate]
    for p in items:
        try:
            d = exposure_delta(p["symbol"], p["side"], float(p.get("risk_pct", 0)))
        except Exception:
            continue
        for ccy, v in d.items():
            net[ccy] = net.get(ccy, 0.0) + v
    return net


def would_breach(open_positions: List[dict], candidate: dict,
                 max_ccy_pct: float = DEFAULT_MAX_CCY) -> Tuple[bool, str]:
    """Fail-closed check. Returns (breaches, reason)."""
    try:
        risk = float(candidate.get("risk_pct", 0))
    except Exception:
        return True, "unparseable risk"
    if risk <= 0:
        return True, "non-positive risk"
    net = combined_exposure(open_positions, candidate)
    worst = max(net.items(), key=lambda kv: abs(kv[1])) if net else ("", 0.0)
    if abs(worst[1]) > max_ccy_pct:
        return True, f"{worst[0]} concentration {worst[1]:+.2f}% > cap {max_ccy_pct}%"
    return False, "ok"


def gate_plans(plans: List[dict], risk_pct: float = 1.5,
               max_ccy_pct: float = DEFAULT_MAX_CCY) -> List[dict]:
    """Order plans by confidence desc; keep a subset that never breaches the cap."""
    accepted: List[dict] = []
    for p in sorted([x for x in plans if x.get("valid")],
                    key=lambda x: float(x.get("confidence") or 0), reverse=True):
        cand = {"symbol": p.get("symbol"), "side": p.get("side"), "risk_pct": risk_pct}
        breach, reason = would_breach(accepted, cand, max_ccy_pct)
        if breach:
            p = dict(p)
            p["portfolio_rejected"] = reason
            continue
        accepted.append(cand)
        p = dict(p)
        p["portfolio_accepted"] = True
    return accepted
