import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "campaign.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        # Bảng chiến dịch chính
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_campaign (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                token TEXT UNIQUE NOT NULL,
                drip_stage INTEGER DEFAULT 1,
                sent_at TEXT,
                last_sent_at TEXT,
                opened_at TEXT,
                clicked_at TEXT,
                failed_at TEXT
            )
        """)
        # Bảng cài đặt hệ thống
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        # Thiết lập mặc định trạng thái Tắt (OFF) ban đầu
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('campaign_status', 'OFF')")
        
        # Thử thêm cột failed_at nếu chưa có
        try:
            conn.execute("ALTER TABLE email_campaign ADD COLUMN failed_at TEXT")
        except sqlite3.OperationalError:
            pass # Cột đã tồn tại
            
        # Thử thêm cột drip_stage và last_sent_at cho Drip Campaign
        try:
            conn.execute("ALTER TABLE email_campaign ADD COLUMN drip_stage INTEGER DEFAULT 1")
            conn.execute("ALTER TABLE email_campaign ADD COLUMN last_sent_at TEXT")
        except sqlite3.OperationalError:
            pass # Cột đã tồn tại
            
        # Thử thêm cột retry_count cho cơ chế Retry
        try:
            conn.execute("ALTER TABLE email_campaign ADD COLUMN retry_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass # Cột đã tồn tại

        conn.commit()

def insert_email(email: str, token: str):
    try:
        with get_conn() as conn:
            conn.execute("INSERT INTO email_campaign (email, token) VALUES (?, ?)", (email, token))
            conn.commit()
    except sqlite3.IntegrityError:
        pass # Email already exists

def mark_sent(email_id: int, current_stage: int):
    with get_conn() as conn:
        now = datetime.now().isoformat()
        if current_stage == 1:
            conn.execute("UPDATE email_campaign SET sent_at = ?, last_sent_at = ?, failed_at = NULL, drip_stage = 2 WHERE id = ?", (now, now, email_id))
        elif current_stage == 2:
            conn.execute("UPDATE email_campaign SET last_sent_at = ?, failed_at = NULL, drip_stage = 3 WHERE id = ?", (now, email_id))
        elif current_stage == 3:
            conn.execute("UPDATE email_campaign SET last_sent_at = ?, failed_at = NULL, drip_stage = 4 WHERE id = ?", (now, email_id))
        conn.commit()

def mark_failed(email_id: int, is_hard_error: bool = False):
    with get_conn() as conn:
        if is_hard_error:
            # Lỗi không thể cứu vãn (VD: Sai định dạng email, Bounced) -> Bỏ qua vĩnh viễn
            conn.execute("UPDATE email_campaign SET failed_at = ? WHERE id = ?", (datetime.now().isoformat(), email_id))
        else:
            # Lỗi hệ thống mạng -> Tăng retry_count. Nếu >= 3 thì mới đánh dấu failed_at
            conn.execute("UPDATE email_campaign SET retry_count = retry_count + 1 WHERE id = ?", (email_id,))
            conn.execute("UPDATE email_campaign SET failed_at = ? WHERE id = ? AND retry_count >= 3", (datetime.now().isoformat(), email_id))
        conn.commit()

def mark_opened(token: str):
    with get_conn() as conn:
        conn.execute("UPDATE email_campaign SET opened_at = ? WHERE token = ? AND opened_at IS NULL", (datetime.now().isoformat(), token))
        conn.commit()

def mark_clicked(token: str):
    with get_conn() as conn:
        conn.execute("UPDATE email_campaign SET clicked_at = ? WHERE token = ? AND clicked_at IS NULL", (datetime.now().isoformat(), token))
        conn.commit()

def get_stats():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM email_campaign").fetchone()[0]
        sent = conn.execute("SELECT COUNT(*) FROM email_campaign WHERE sent_at IS NOT NULL").fetchone()[0]
        opened = conn.execute("SELECT COUNT(*) FROM email_campaign WHERE opened_at IS NOT NULL").fetchone()[0]
        clicked = conn.execute("SELECT COUNT(*) FROM email_campaign WHERE clicked_at IS NOT NULL").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM email_campaign WHERE failed_at IS NOT NULL").fetchone()[0]
        return {
            "total_emails": total,
            "total_sent": sent,
            "total_opened": opened,
            "total_clicked": clicked,
            "total_failed": failed
        }

def get_daily_stats():
    with get_conn() as conn:
        # Nhóm theo ngày gửi
        rows = conn.execute("""
            SELECT 
                substr(sent_at, 1, 10) as send_date, 
                COUNT(*) as count 
            FROM email_campaign 
            WHERE sent_at IS NOT NULL 
            GROUP BY send_date 
            ORDER BY send_date DESC
        """).fetchall()
        
        # Nhóm theo ngày lỗi
        failed_rows = conn.execute("""
            SELECT 
                substr(failed_at, 1, 10) as fail_date, 
                COUNT(*) as count 
            FROM email_campaign 
            WHERE failed_at IS NOT NULL 
            GROUP BY fail_date
        """).fetchall()
        
        fail_dict = {row['fail_date']: row['count'] for row in failed_rows}
        
        result = []
        for row in rows:
            d = row['send_date']
            result.append({
                "date": d,
                "sent": row['count'],
                "failed": fail_dict.get(d, 0)
            })
        return result

def get_unsent_emails(limit=50):
    with get_conn() as conn:
        # Lấy những email chưa được click VÀ
        # (Chưa gửi bao giờ OR (Đã gửi stage trước đó và cách đây ít nhất 24 tiếng) VÀ stage < 4)
        query = """
            SELECT id, email, token, drip_stage, last_sent_at 
            FROM email_campaign 
            WHERE clicked_at IS NULL 
            AND failed_at IS NULL
            AND drip_stage <= 3
            AND (
                last_sent_at IS NULL 
                OR 
                (julianday('now') - julianday(last_sent_at)) >= 1.0
            )
            LIMIT ?
        """
        return conn.execute(query, (limit,)).fetchall()

def get_campaign_status():
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'campaign_status'").fetchone()
        return row['value'] if row else 'OFF'

def toggle_campaign_status():
    with get_conn() as conn:
        current = get_campaign_status()
        new_status = 'ON' if current == 'OFF' else 'OFF'
        conn.execute("UPDATE settings SET value = ? WHERE key = 'campaign_status'", (new_status,))
        conn.commit()
        return new_status

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
