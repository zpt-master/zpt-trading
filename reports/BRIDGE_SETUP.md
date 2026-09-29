# Hướng dẫn kết nối MT5 bridge (cho creator)

Bạn báo "MT5 bridge đã hoạt động trở lại". Adapter của tôi đã sẵn sàng và đã test
end-to-end (mock server, 5/5 PASS). Tôi chỉ còn thiếu **địa chỉ (base_url)** của bridge
vì sandbox của tôi bị giới hạn egress — tôi không tự dò được sang máy Windows host.

## Cách 1 (nhanh nhất) — chạy 1 lệnh
```bash
cd /home/oroth/trading
./setup_bridge.sh http://<host>:<port> [api_key]
```
Ví dụ nếu bridge chạy trên Windows host và WSL2 thấy host ở 172.27.176.1:
```bash
./setup_bridge.sh http://172.27.176.1:5000
```
Lệnh này ghi `config/mt5.json` rồi tự chạy preflight (`/account`, `/price`).

## Cách 2 — đặt biến môi trường
```bash
export MT5_BRIDGE_URL=http://<host>:<port>
export MT5_API_KEY=<key>          # nếu bridge yêu cầu
cd /home/oroth/trading && ./setup_bridge.sh
```

## Bridge cần cung cấp (hợp đồng HTTP/JSON)
| Method | Path | Trả về |
|--------|------|--------|
| GET  | /account | `{"equity":..,"balance":..,"currency":"USD","broker":..}` |
| GET  | /price?symbol=EURUSD | `{"bid":..,"ask":..}` hoặc `{"price":..}` |
| POST | /order | body `{symbol,direction,entry,stop,target,lots}` → `{"ok":true,"ticket":..}` |
| POST | /close | body `{ticket}` → `{"ok":true}` |
| GET  | /positions | danh sách vị thế đang mở |

Adapter của tôi **tự dò** các biến thể phổ biến (bid/ask, price, retcode 10009...), nên
nhiều bridge dùng luôn được mà không cần sửa code. Nếu đường dẫn khác, sửa mục `paths`
trong `config/mt5.json`.

## Sau khi kết nối
1. `python3 live_trader.py --preflight`  → xác nhận đọc được tài khoản + giá.
2. `python3 live_trader.py --dry-run`    → xem kế hoạch, KHÔNG đặt lệnh.
3. Đặt `"live": true` trong `config/mt5.json` → mới giao dịch thật.

## Quy tắc rủi ro (cứng, không thể ghi đè bằng chiến lược)
- Rủi ro ≤ 1.5% vốn/lệnh · STOP-LOSS bắt buộc · R:R ≥ 1.5 · tổng rủi ro mở ≤ 4%
- Giới hạn lỗ ngày 5% → tự dừng trong ngày
- Kill-switch: tạo file `DISABLE_LIVE` hoặc `export MT5_KILL=1`

## Nguyên tắc lãi/vốn (theo genesis)
- Lãi trả 08:00 GMT+7 hàng ngày; vốn = balance MT5 sau khi trả lãi.
- Nếu lỗ, lấy balance cao nhất làm mốc (drawdown high-water mark) — ngày nào không vượt
  mốc đó vẫn tính là lỗ.
- Tỷ lệ MT5 : phí hoạt động = 1:1 (1 USD = 1 USD).
