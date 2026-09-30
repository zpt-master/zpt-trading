# Nukida strategy study (nukida.co)

Core thesis captured from the site: **value is decided by money flow (dòng tiền), not by charts or news.**

Key ideas:
- Money flow / dòng tiền is the primary driver of price.
- Discipline & risk come before prediction (fear of entering = fear of stoploss).
- Simplicity beats complexity ('làm những thứ đơn giản').
- AQ (adversity quotient) > IQ/EQ for survival as a trader.

Article titles seen:
- Tự do là &#8220;vô giá&#8221;
- Chỉ số AQ &#8211; Chỉ số quan trọng nhất
- Chuyện&#8230; Sợ vào lệnh!
- Chuyện… VAY NỢ!
- Làm những thứ đơn giản&#8230;
- Giá trị một tài sản được quyết định bởi&#8230;
- Gốc rễ của việc rèn TÂM LÝ GIAO DỊCH?
- Học nhiều chưa chắc giỏi!
- Trading có thể trở thành một nghề hay không?

## Encoded as a testable rule (rule_moneyflow in eval_harness.py)

Flow proxy = Σ (close−open)·range over window, normalized by price. Long when
net flow strongly positive, short when strongly negative, flat otherwise.
Mandatory ATR stop + fixed R:R, walk-forward OOS.

Result (6 symbols):
| symbol | n | hit | exp | t | verdict |
|---|---|---|---|---|---|
| XAUUSD | 43 | 0.35 | -0.035R | -0.20 | no |
| USDJPY | 21 | 0.14 | -0.595R | **-3.02** | no (significant REVERSAL) |
| GBPUSD |  5 | 0.20 | -0.300R | -0.61 | no |
| AUDUSD | 15 | 0.27 | -0.133R | -0.47 | no |
| USDCAD | 19 | 0.68 | +0.763R | +2.93 | nominal EDGE |
| EURUSD |  4 | too few | - | - | no |

**Verdict: EDGE NOT PROVEN.** One nominally-positive symbol out of six, with a
*significant negative* on another, is the signature of multiple-testing noise —
not a exploitable money-flow signal. Capital stays safe.
