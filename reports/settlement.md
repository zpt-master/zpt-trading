# MT5 → Internal settlement (high-water-mark)

Generated: 2026-09-29T09:31:42.058968+07:00

- Trading balance: **100425.38 USD**
- Equity: 100425.55
- High-water mark (mt5_hwm): **100425.41**
- Period peak: 100425.41
- Next payout: **2026-09-30 08:00 GMT+7**
- Settlement enabled: True @ hour 1 UTC (08:00 GMT+7)
- Internal balance: 96934.00805868224 cents (tier high)

Rule: at 08:00 GMT+7 the rise of the period peak above the mark is credited
(1 USD = 100 cents = 1:1). If peak <= mark, the day counts as a loss and the
mark is NOT lowered (drawdown high-water mark) — per genesis.
