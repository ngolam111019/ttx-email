import database as db
with db.get_conn() as conn:
    conn.execute("UPDATE email_campaign SET sent_at = NULL WHERE sent_at = 'WAITING_FOR_PROD'")
    conn.commit()
print("Reverted successfully!")
