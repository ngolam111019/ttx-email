import database as db

TEST_EMAILS = [
    "ngothanhlamit@gmail.com",
    "ngolam11101993@gmail.com",
    "dtruong1119@gmail.com"
]

def prepare_sandbox():
    print("Preparing Sandbox Testing Environment...")
    with db.get_conn() as conn:
        # Tạm thời khóa tất cả 62k email lại (để không bị gửi nhầm gây lỗi)
        # Bằng cách set sent_at thành 1 giá trị đặc biệt
        conn.execute("UPDATE email_campaign SET sent_at = 'WAITING_FOR_PROD' WHERE sent_at IS NULL AND email NOT IN (?, ?, ?)", 
                     (TEST_EMAILS[0], TEST_EMAILS[1], TEST_EMAILS[2]))
        
        print(f"Locked non-verified emails.")
        
        # Đảm bảo 3 email test có mặt trong database và sẵn sàng gửi
        for email in TEST_EMAILS:
            # Thêm mới nếu chưa có
            token = f"sandbox_token_{email.split('@')[0]}"
            try:
                conn.execute("INSERT INTO email_campaign (email, token) VALUES (?, ?)", (email, token))
            except:
                pass # Bỏ qua nếu đã tồn tại
                
            # Đảm bảo 3 email này được phép gửi
            conn.execute("UPDATE email_campaign SET sent_at = NULL, failed_at = NULL WHERE email = ?", (email,))
            
        conn.commit()
        print(f"Unlocked 3 test emails for sending.")
        
        # In ra số lượng đang chờ gửi
        count = conn.execute("SELECT COUNT(*) FROM email_campaign WHERE sent_at IS NULL AND failed_at IS NULL").fetchone()[0]
        print(f"Total emails ready to send right now: {count}")

if __name__ == "__main__":
    prepare_sandbox()
