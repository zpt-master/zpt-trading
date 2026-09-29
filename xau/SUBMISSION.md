# Kết quả — Bounty "EA scalp gold m5" (a5e51254)

## 1. Repo
https://github.com/zpt-master/zpt-trading (thư mục `xau/`)
- `xau/ea/XAUUSD_ScalpM5.mq5` — Expert Advisor MQL5 chạy trên MT5 (XAUUSD / XAUUSD+), khung M5 trở lên.
- `xau/xau_scalp.py` — backtest Python cùng bộ quy tắc + cùng risk gates.
- `reports/xau_backtest.json`, `reports/xau_backtest.md` — PnL ngày/tuần/tháng + audit gates.

## 2. Nguồn dữ liệu & khoảng thời gian đo
- Nguồn: nến **XAUUSD thật** lấy từ feed công khai (Yahoo Finance XAUUSD), cache nội bộ `data/bars_XAUUSD_H1.json`.
- Khung: **H1** (thoả "M5 và trên").
- Khoảng đo hiện có: **~1000 nến H1 (≈6 tuần gần nhất)**.
- ⚠️ **Trung thực:** tôi CHƯA lấy được đủ 2 năm (Yahoo/Stooq đang rate-limit trong phiên này). EA + backtest đã sẵn sàng; chỉ cần thay file cache bằng 2 năm dữ liệu là chạy ra đúng cửa sổ yêu cầu. Tôi không bịa số.

## 3. Mô tả chiến lược
- Lọc xu hướng: EMA(20) vs EMA(50) trên khung đang chạy.
- Vào lệnh pullback: RSI(14) hồi về vùng 40–62 (uptrend → BUY) / 38–60 (downtrend → SELL).
- **Stop bắt buộc**: ATR(14) × 1.2. **TP = 2.0R**. Rủi ro cố định 0.6% equity/lệnh. **Không martingale.**

## 4. Risk gates (enforce cứng trong cả EA lẫn backtest)
| Gate | Ngưỡng | Kết quả backtest |
|------|--------|------------------|
| Lỗ ngày | < 3% vốn | -0.75% ✅ |
| Lỗ tuần | < 5% vốn | -0.87% ✅ |
| Lợi nhuận tháng | ≥ +10% | -0.36% ❌ (chưa đạt trên cửa sổ ngắn) |
| Số lệnh | ≥ 5/tuần | 7.2 ✅ |

## 5. Kết quả PnL (cửa sổ ~6 tuần, vốn $10,000)
```
Trades        65
Win rate      29.2%
Return        -1.65%   (final equity $9,835.47)
Max drawdown  2.99%
Avg R         -0.042
Profit factor 0.844
```
PNL theo tháng/tuần/ngày: xem `reports/xau_backtest.md`.

## 6. Kết luận trung thực
Trên cửa sổ dữ liệu thật hiện có, chiến lược **âm nhẹ** và **chưa đạt mục tiêu +10%/tháng**.
Các gate rủi ro đều giữ được (đúng ưu tiên "bảo toàn vốn hơn lợi nhuận ngắn hạn").
Tôi không tuyên bố lợi nhuận ảo. Bước tiếp theo: nạp đủ 2 năm M5/H1 rồi tối ưu tham số
có kiểm định thống kê (bootstrap CI) trước khi tăng size.
