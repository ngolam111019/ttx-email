import database as db

TEST_EMAILS = [
    "ngothanhlamit@gmail.com",
    "ngolam11101993@gmail.com",
    "dtruong1119@gmail.com"
]

def prepare_sandbox():
    print("Preparing Sandbox Testing Environment...")
    with db.get_conn() as conn:
        # Khóa tất cả 62k email bằng cách set drip_stage = 99
        conn.execute("UPDATE email_campaign SET drip_stage = 99 WHERE email NOT IN (?, ?, ?)", 
                     (TEST_EMAILS[0], TEST_EMAILS[1], TEST_EMAILS[2]))
        
        print(f"Locked non-verified emails (drip_stage = 99).")
        
        # Đảm bảo 3 email test có mặt và drip_stage = 1, last_sent_at = NULL
        for email in TEST_EMAILS:
            token = f"sandbox_token_{email.split('@')[0]}"
            try:
                conn.execute("INSERT INTO email_campaign (email, token) VALUES (?, ?)", (email, token))
            except:
                pass # Bỏ qua nếu đã tồn tại
                
            conn.execute("UPDATE email_campaign SET drip_stage = 1, last_sent_at = NULL, sent_at = NULL, failed_at = NULL, clicked_at = NULL WHERE email = ?", (email,))
            
        conn.commit()
        print(f"Unlocked 3 test emails for sending Stage 1.")
        
        count = conn.execute("SELECT COUNT(*) FROM email_campaign WHERE drip_stage = 1").fetchone()[0]
        print(f"Total emails ready to send right now: {count}")

if __name__ == "__main__":
    prepare_sandbox()
