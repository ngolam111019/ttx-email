import database as db
with db.get_conn() as conn:
    conn.execute("UPDATE email_campaign SET sent_at = NULL WHERE email IN ('ngothanhlamit@gmail.com', 'ngolam11101993@gmail.com', 'dtruong1119@gmail.com')")
    conn.commit()
print("Reset DB!")
