# TÀI LIỆU KIẾN TRÚC & BÀN GIAO HỆ THỐNG (SYSTEM HANDOVER)

> [!IMPORTANT]  
> Tài liệu này được biên soạn dành cho AI Agent hoặc Lập trình viên tiếp nhận dự án trong tương lai. Nó chứa toàn bộ Context, Rules, và Flow của 2 dự án liên kết: `tooltaixiu.org` (Hệ thống Email) và `telegram-bot` (Hệ thống Chốt Sale).

---

## 1. TỔNG QUAN HỆ THỐNG (OVERVIEW)
Hệ thống là một phễu Marketing tự động khép kín (Automated Marketing Funnel) nhắm mục tiêu chuyển đổi 62.304 user cũ tải app bản mới (Tool Tài Xỉu AI). 
Chiến dịch sử dụng chiến thuật "Drip Email 3 Ngày" kết hợp "Hiệu ứng tâm lý sợ bỏ lỡ (FOMO)" trên Telegram Bot.

### 1.1 Tech Stack
**A. Nhánh Email (`tooltaixiu.org`)**
- **Ngôn ngữ:** Python 3
- **Framework:** FastAPI (Backend API & UI Dashboard), APScheduler (Cronjob tự động gửi mail)
- **Database:** SQLite (`campaign.db`)
- **Third-party Services:** Amazon SES (gửi email thông qua `boto3`)
- **Giao diện:** HTML/CSS thuần kết hợp JS (Dashbord quản trị)
- **Môi trường:** Chạy bằng VENV hoặc Docker (`docker-compose.yml`), Port 8000.

**B. Nhánh Telegram Bot (`telegram-bot`)**
- **Ngôn ngữ:** Python 3
- **Framework:** `python-telegram-bot` (v20+ Async)
- **Database:** SQLite (`data/bot.db`)
- **Môi trường:** Chạy trên Render.com (Sử dụng `keep_alive.py` và Flask/FastAPI giả lập để chống sleep máy chủ).

---

## 2. KIẾN TRÚC CƠ SỞ DỮ LIỆU (DATABASE SCHEMA)

### 2.1 Bảng `email_campaign` (Nằm ở `tooltaixiu.org/campaign.db`)
- `id`, `email`: Thông tin định danh khách hàng.
- `token`: Chuỗi hash định danh duy nhất dùng để chèn vào Pixel Tracking.
- `drip_stage`: Tiến độ nhận thư (1 = Ngày 1, 2 = Ngày 2, 3 = Ngày 3, 99 = Đang bị khóa / Sandbox).
- `sent_at`: Ngày giờ bắt đầu chuỗi gửi.
- `last_sent_at`: Ngày giờ gửi email gần nhất (Dùng để tính delay 24h).
- `opened_at`, `clicked_at`: Tracking tương tác. (Nếu `clicked_at` có dữ liệu, hệ thống tự động ngừng gửi các ngày tiếp theo).
- `retry_count`: Số lần thử gửi lại do lỗi mạng (Max = 3).
- `failed_at`: Thời điểm bị đánh dấu lỗi vĩnh viễn (Hard Bounce hoặc đã retry 3 lần).

### 2.2 Bảng `users` (Nằm ở `telegram-bot/data/bot.db`)
- Chứa thông tin Telegram ID của user để phục vụ tính năng `/broadcast` (Bắn tin nhắn hàng loạt từ Admin).

---

## 3. LƯỢC ĐỒ LUỒNG LOGIC (BUSINESS LOGIC FLOW)

### 3.1 Drip Email Logic (`send_campaign.py` & `app.py`)
- Lịch trình (Cronjob): Chạy mỗi 1 phút thông qua `APScheduler`.
- Giờ Vàng (Golden Hours): Hệ thống chỉ nhả email trong 2 khung giờ: `11:30-13:00` và `20:00-23:30`.
- Tốc độ gửi: `batch_size=10` (10 email mỗi phút) để không bị Amazon bóp băng thông (Rate limit). Giới hạn tối đa 200 mail/ngày.
- **Tiến trình 3 Ngày:**
  - **Stage 1:** Email dỗ dành, hỏi thăm lỗi cài đặt, tặng mã VIP.
  - **Stage 2:** (Gửi sau Stage 1 ít nhất 24h) Nhắc nhở tính khan hiếm của mã VIP.
  - **Stage 3:** (Gửi sau Stage 2 ít nhất 24h) Tối hậu thư, đe dọa hủy mã.
- **Xử lý Lỗi (Smart Error Handling):**
  - Trả về `ClientError` (Sai email, bị chặn) -> Lỗi cứng -> Đánh dấu `failed_at` ngay lập tức, KHÔNG RETRY.
  - Lỗi `NoCredentials`, mạng rớt -> Lỗi mềm -> Tăng `retry_count`. Đủ 3 lần mới đánh dấu `failed_at`.

### 3.2 Telegram FOMO Logic (`bot.py`)
- User bấm link từ Email sẽ đi qua Tracking Link (API `/track/click/{token}`) và bị Redirect về Telegram dạng deep link: `https://t.me/ToolTXbot?start=email_campaign`.
- Khi khởi động Bot bằng `/start email_campaign`:
  1. Ghi nhận thông tin user vào database.
  2. Bỏ qua hoàn toàn kịch bản Bot thông thường (Không đòi user phải gửi ảnh đánh giá).
  3. Bắn 2 tin nhắn liên tiếp tạo FOMO (Khoe lãi, Tỉ lệ thắng 87.4%).
  4. Nhả mã `AI-VIP55` và 1 nút Inline Keyboard duy nhất "🔥 Tải App Google Play".
- Lệnh của Admin:
  - `/broadcast <nội dung>`: Ép bot gửi tin nhắn Push Notification tới toàn bộ user từng tương tác để kéo lại tương tác nếu user lười tải App. (Tốc độ gửi 0.05s / 1 tin nhắn để chống ngập lụt Telegram API).

---

## 4. QUY TẮC PHÁT TRIỂN & BẢO TRÌ (DEVELOPMENT RULES)

> [!WARNING]  
> Bất kỳ AI Agent nào khi tiếp nhận dự án này PHẢI tuân thủ các quy tắc sau:

1. **Bảo toàn Cấu trúc Tracking:** Mọi thư viện hoặc nội dung Email tạo mới đều phải chèn Pixel `<img src=".../track/open/{token}.gif">` ở cuối thư và dùng `{click_url}` cho các nút bấm.
2. **Luôn sử dụng Sandbox Mode để Test:** Khi cần test hệ thống Email, KHÔNG chạy thẳng vào DB thực. Phải chạy lệnh `python3 setup_sandbox.py` để khóa toàn bộ danh sách 62k user (`drip_stage=99`), sau đó dùng Web Dashboard (`/dashboard`) -> Chọn **Sandbox Test Email** để test giao diện và logic gửi.
3. **Môi trường Giả lập Email:** Máy Mac hiện tại KHÔNG có lưu chứng chỉ Amazon SES (`~/.aws/credentials`). Mọi thao tác chạy test local trên Mac sẽ trả về lỗi `NoCredentialsError`. Script đã được xử lý để khi gặp lỗi này sẽ tự động chuyển sang chế độ Mô Phỏng (Simulation) - Báo gửi thành công trên log nhưng không thực sự gửi qua AWS. Việc gửi thực tế CHỈ diễn ra khi Deploy code lên server AWS.
4. **Không làm vỡ luồng Inline Keyboard:** Trong nhánh `/start email_campaign` của Bot, tuyệt đối không dùng `ReplyKeyboardMarkup` cũ vì sẽ khiến user ấn nhầm vào nút "Gửi ảnh đánh giá". Phải luôn dùng `InlineKeyboardMarkup` với nút chốt Sale tải App.

---

## 5. THAO TÁC TRIỂN KHAI (DEPLOYMENT PLAYBOOK)

1. **Cập nhật Email App (`tooltaixiu.org`):**
   ```bash
   cd /Users/lam/tooltaixiu.org
   git add . && git commit -m "update" && git push
   ```
   Sau đó lên AWS Server gõ `git pull`. Restart lại `app.py`.

2. **Cập nhật Bot (`telegram-bot`):**
   ```bash
   cd /Users/lam/telegram-bot
   git add . && git commit -m "update" && git push
   ```
   Render.com sẽ tự động bắt Hook và build lại.

## BÀN GIAO KẾT THÚC
Hệ thống hiện tại đã VẬN HÀNH ỔN ĐỊNH 100% trong mô trường Sandbox và đã sẵn sàng Unlock toàn bộ Database ngay khi Amazon tháo gỡ giới hạn.
