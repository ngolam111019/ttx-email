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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_campaign (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                token TEXT UNIQUE NOT NULL,
                sent_at TEXT,
                opened_at TEXT,
                clicked_at TEXT
            )
        """)
        conn.commit()

def insert_email(email: str, token: str):
    try:
        with get_conn() as conn:
            conn.execute("INSERT INTO email_campaign (email, token) VALUES (?, ?)", (email, token))
            conn.commit()
    except sqlite3.IntegrityError:
        pass # Email already exists

def mark_sent(email_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE email_campaign SET sent_at = ? WHERE id = ?", (datetime.now().isoformat(), email_id))
        conn.commit()

def mark_opened(token: str):
    with get_conn() as conn:
        # Only set opened_at if it's currently NULL (to track the first open time)
        conn.execute("UPDATE email_campaign SET opened_at = ? WHERE token = ? AND opened_at IS NULL", (datetime.now().isoformat(), token))
        conn.commit()

def mark_clicked(token: str):
    with get_conn() as conn:
        # Only set clicked_at if it's currently NULL
        conn.execute("UPDATE email_campaign SET clicked_at = ? WHERE token = ? AND clicked_at IS NULL", (datetime.now().isoformat(), token))
        conn.commit()

def get_stats():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM email_campaign").fetchone()[0]
        sent = conn.execute("SELECT COUNT(*) FROM email_campaign WHERE sent_at IS NOT NULL").fetchone()[0]
        opened = conn.execute("SELECT COUNT(*) FROM email_campaign WHERE opened_at IS NOT NULL").fetchone()[0]
        clicked = conn.execute("SELECT COUNT(*) FROM email_campaign WHERE clicked_at IS NOT NULL").fetchone()[0]
        return {
            "total_emails": total,
            "total_sent": sent,
            "total_opened": opened,
            "total_clicked": clicked
        }

def get_unsent_emails(limit=100):
    with get_conn() as conn:
        return conn.execute("SELECT id, email, token FROM email_campaign WHERE sent_at IS NULL LIMIT ?", (limit,)).fetchall()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
