# zpt trading

Conservative MT5 forex engine. Talks to Vantage only through the local bridge
(localhost:4790) — never sees broker credentials.

- `feed.py`       price feed (Yahoo chart API, stdlib only)
- `indicators.py` EMA / RSI / ATR
- `strategy.py`   EMA20/50 cross + RSI filter, ATR-based SL/TP (RR 1.5)
- `risk.py`       hard risk gates: 1% risk/trade, max 6 trades/day, max 3 open,
                  -3% daily loss cap, 3 consecutive losses -> 24h cooldown
- `engine.py`     one cycle: feed -> strategy -> risk -> bridge. `DRY_RUN` or `LIVE`
- `report.py`     daily settlement vs high-water (creator's 1:1 rule)
- `logs/`         engine.log + report-YYYY-MM-DD.md

Run: `python3 engine.py DRY_RUN` then `python3 engine.py LIVE`
