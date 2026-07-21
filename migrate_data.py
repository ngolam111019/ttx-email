import psycopg2
import sqlite3
import re
import dns.resolver
import uuid
import database as db
import logging
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format='%(message)s')

POSTGRES_DSN = "postgresql://postgres:123456@localhost:5433/tooltx"

DISPOSABLE_DOMAINS = {
    'mailinator.com', '10minutemail.com', 'yopmail.com', 'guerrillamail.com',
    'tempmail.com', 'temp-mail.org', 'throwawaymail.com', 'dispostable.com'
}

ROLE_BASED_PREFIXES = {
    'admin', 'support', 'info', 'noreply', 'no-reply', 'test', 'contact', 'sales', 'billing'
}

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

def is_valid_syntax(email):
    return bool(EMAIL_REGEX.match(email))

def is_role_based_or_disposable(email):
    try:
        local_part, domain = email.lower().split('@')
        if local_part in ROLE_BASED_PREFIXES:
            return True
        if domain in DISPOSABLE_DOMAINS:
            return True
        return False
    except ValueError:
        return True

def has_mx_record(email):
    try:
        domain = email.split('@')[1]
        # Resolve MX records
        answers = dns.resolver.resolve(domain, 'MX')
        return len(answers) > 0
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout, Exception):
        return False

def clean_and_insert_emails():
    logging.info("⏳ Connecting to Postgres...")
    try:
        pg_conn = psycopg2.connect(POSTGRES_DSN)
        pg_cursor = pg_conn.cursor()
    except Exception as e:
        logging.error(f"❌ Failed to connect to Postgres: {e}")
        return

    # 1. Fetch data from both tables
    logging.info("📥 Fetching raw data from Postgres...")
    
    raw_emails = set()
    
    # Table: users, Column: phone
    try:
        pg_cursor.execute("SELECT phone FROM users WHERE phone IS NOT NULL AND phone != ''")
        for row in pg_cursor.fetchall():
            raw_emails.add(str(row[0]).strip().lower())
        logging.info(f"   - Fetched from users.phone")
    except Exception as e:
        logging.warning(f"   - Could not fetch from users: {e}")

    # Table: n_users, Column: email
    try:
        pg_cursor.execute("SELECT email FROM n_users WHERE email IS NOT NULL AND email != ''")
        for row in pg_cursor.fetchall():
            raw_emails.add(str(row[0]).strip().lower())
        logging.info(f"   - Fetched from n_users.email")
    except Exception as e:
        logging.warning(f"   - Could not fetch from n_users: {e}")
        
    pg_conn.close()

    total_raw = len(raw_emails)
    logging.info(f"📊 Total raw unique strings fetched: {total_raw}")

    # 2. Syntax & Role-based filtering (Fast)
    logging.info("🧹 Applying Syntax and Role-based filters...")
    syntax_passed = set()
    for email in raw_emails:
        if is_valid_syntax(email) and not is_role_based_or_disposable(email):
            syntax_passed.add(email)
            
    logging.info(f"   - Removed {total_raw - len(syntax_passed)} invalid or role-based emails.")
    logging.info(f"   - Remaining for DNS check: {len(syntax_passed)}")

    # 3. MX Record Validation (Slow, use ThreadPool)
    logging.info("🌐 Checking DNS/MX Records (This might take a while)...")
    valid_emails = []
    
    # We use a smaller subset if it's too large for a quick run, but let's process all using threads
    def check_dns(email):
        if has_mx_record(email):
            return email
        return None

    # Using threads to speed up DNS resolution
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_dns, syntax_passed)
        
    for res in results:
        if res:
            valid_emails.append(res)
            
    logging.info(f"   - Removed {len(syntax_passed) - len(valid_emails)} emails with dead domains.")
    
    # 4. Insert into SQLite
    logging.info(f"💾 Inserting {len(valid_emails)} clean emails into SQLite...")
    db.init_db() # Ensure table exists
    
    inserted_count = 0
    duplicate_sqlite_count = 0
    
    for email in valid_emails:
        token = uuid.uuid4().hex
        try:
            db.insert_email(email, token)
            inserted_count += 1
        except Exception:
            duplicate_sqlite_count += 1
            
    logging.info("✅ Migration Complete!")
    logging.info("=========================================")
    logging.info(f"Total Raw Read        : {total_raw}")
    logging.info(f"Syntax/Role Removed   : {total_raw - len(syntax_passed)}")
    logging.info(f"Dead Domains Removed  : {len(syntax_passed) - len(valid_emails)}")
    logging.info(f"Successfully Inserted : {inserted_count}")
    logging.info("=========================================")

if __name__ == "__main__":
    clean_and_insert_emails()
