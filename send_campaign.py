import time
import boto3
import database as db
from botocore.exceptions import ClientError
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# TODO: Add your AWS SES Region and Credentials (or use IAM roles if deployed on EC2)
AWS_REGION = "us-east-1"
SENDER = "Admin <admin@tooltaixiu.org>"

# Configure SES Client
try:
    ses_client = boto3.client('ses', region_name=AWS_REGION)
except Exception as e:
    logging.error(f"Failed to initialize SES client: {e}")
    ses_client = None

def create_email_html(token: str) -> str:
    # URL Tracking for clicks (replace with your actual domain when deployed)
    TRACKING_DOMAIN = "http://localhost:8000"
    click_url = f"{TRACKING_DOMAIN}/track/click/{token}"
    open_pixel_url = f"{TRACKING_DOMAIN}/track/open/{token}.gif"

    html = f"""
    <html>
    <head></head>
    <body>
        <p>Chào bạn,</p>
        <p>Đây là kết quả thực tế của App Tool Tài Xỉu AI thế hệ mới.</p>
        <p>Vì bạn là người dùng cũ, tôi dành riêng cho bạn <b>Mã giảm giá 55% trọn đời</b> để mở khoá tính năng VIP. Tuy nhiên, chỉ có đúng 500 mã.</p>
        <p><b>Để nhận được mã này, bạn chỉ cần làm 2 bước đơn giản:</b></p>
        <ol>
            <li>Tải App và để lại Đánh giá 5 Sao trên cửa hàng.</li>
            <li>Chụp màn hình đánh giá của bạn và gửi vào Bot Telegram của chúng tôi.</li>
        </ol>
        <p>👉 <a href="{click_url}" style="font-weight:bold; color: #3b82f6;">Click vào đây để mở Bot Telegram tự động</a></p>
        
        <!-- Tracking Pixel -->
        <img src="{open_pixel_url}" width="1" height="1" style="display:none;" />
    </body>
    </html>
    """
    return html

def create_email_text(token: str) -> str:
    TRACKING_DOMAIN = "http://localhost:8000"
    click_url = f"{TRACKING_DOMAIN}/track/click/{token}"

    text = f"""Chào bạn,

Đây là kết quả thực tế của App Tool Tài Xỉu AI thế hệ mới.
Vì bạn là người dùng cũ, tôi dành riêng cho bạn Mã giảm giá 55% trọn đời để mở khoá tính năng VIP. Tuy nhiên, chỉ có đúng 500 mã.

Để nhận được mã này, bạn chỉ cần làm 2 bước đơn giản:
1. Tải App và để lại Đánh giá 5 Sao trên cửa hàng.
2. Chụp màn hình đánh giá của bạn và gửi vào Bot Telegram của chúng tôi.

👉 Link Bot Telegram: {click_url}
"""
    return text


def send_email(to_address: str, token: str):
    if not ses_client:
        logging.error("SES client is not initialized. Skipping send.")
        return False

    subject = "App AI mới đã sẵn sàng (Và 1 nhiệm vụ nhỏ cho bạn)"
    html_body = create_email_html(token)
    text_body = create_email_text(token)

    try:
        response = ses_client.send_email(
            Destination={
                'ToAddresses': [to_address],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': "UTF-8",
                        'Data': html_body,
                    },
                    'Text': {
                        'Charset': "UTF-8",
                        'Data': text_body,
                    },
                },
                'Subject': {
                    'Charset': "UTF-8",
                    'Data': subject,
                },
            },
            Source=SENDER,
        )
    except ClientError as e:
        logging.error(f"Error sending to {to_address}: {e.response['Error']['Message']}")
        return False
    else:
        logging.info(f"Email sent to {to_address}! Message ID: {response['MessageId']}")
        return True

def run_campaign(batch_size=100, delay_seconds=1):
    logging.info("Fetching unsent emails...")
    unsent_emails = db.get_unsent_emails(limit=batch_size)
    
    if not unsent_emails:
        logging.info("No unsent emails found. Campaign might be complete.")
        return

    logging.info(f"Found {len(unsent_emails)} targets for this batch.")
    
    for row in unsent_emails:
        email_id = row['id']
        email = row['email']
        token = row['token']

        # NOTE: For local testing without AWS credentials, you can comment out send_email
        # and just simulate sending to test the tracking logic.
        success = send_email(email, token)
        
        # Simulate success for testing if AWS is not configured
        if not ses_client:
            logging.info(f"[SIMULATION] Sent email to {email} with token {token}")
            success = True

        if success:
            db.mark_sent(email_id)
        else:
            db.mark_failed(email_id)
        
        time.sleep(delay_seconds) # Rate limiting to avoid SES throttle

if __name__ == "__main__":
    # Ensure DB is initialized
    db.init_db()
    # Run one batch
    run_campaign(batch_size=10, delay_seconds=1)
