# Live MT5 Bridge (risk-governed)

Two halves — the agent never bypasses risk limits, and the broker enforces them too.

## 1. Broker side (MQL5 Expert Advisor)
Copy `MQL5/Experts/ZptGovEA.mq5` into your MT5 data folder
(`File > Open Data Folder > MQL5 > Experts`), then compile in MetaEditor.
Attach to ONE chart any symbol; it governs ALL symbols via shared files.

Permissions: allow `Algo Trading`; set `InpDryRun=false` only when ready.

### Hard rules enforced ON the broker (cannot be overridden by a signal)
- max risk per order ≤ **1.5%** equity  ·  **mandatory stop-loss**
- reward:risk ≥ **1.5**  ·  lot cap **5.0**  ·  aggregate open risk ≤ **4%**
- **no martingale, no averaging into losers**

## 2. Agent side (Python)
`mt5_bridge_file.py` writes governed signals to `zpt_signals.csv` and reads
`zpt_state.json` back. Only plans with a real stop and RR≥1.5 are pushed.

```bash
export MT5_COMMON="$HOME/.wine/drive_c/.../Terminal/Common/Files"   # if not auto-detected
python3 mt5_bridge_file.py        # prints bridge state + governed push
```

## 3. Settlement
`settle(day, hwm, equity)` reconciles payouts (1 USD = 100 cents) against a
high-water mark. Losses never lower the HWM — the honest, drawdown-aware rule
from the genesis spec.
