"""fxintel — dependency-free FX/metals market intelligence engine.

Pure Python. No third-party imports. Computes trend regime, momentum,
volatility state, and produces an actionable, risk-aware summary.
"""
from .indicators import ema, sma, rsi, atr, adx
from .regime import classify
from .summary import summarize
__version__ = "0.1.0"
__all__ = ["ema","sma","rsi","atr","adx","classify","summarize"]
