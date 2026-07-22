import time
import boto3
import database as db
from botocore.exceptions import ClientError
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# TODO: Add your AWS SES Region and Credentials (or use IAM roles if deployed on EC2)
AWS_REGION = "ap-southeast-1"
SENDER = "Admin <admin@tooltaixiu.org>"

# Configure SES Client
try:
    ses_client = boto3.client('ses', region_name=AWS_REGION)
except Exception as e:
    logging.error(f"Failed to initialize SES client: {e}")
    ses_client = None

def create_email_html(token: str) -> str:
    # URL Tracking for opens
    # Tạm thời đổi về IP của Server (Lý tưởng nhất sau này nên trỏ 1 tên miền như api.tooltaixiu.org về IP này để chống spam)
    TRACKING_DOMAIN = "http://54.254.130.124"
    open_pixel_url = f"{TRACKING_DOMAIN}/track/open/{token}.gif"
    click_url = f"{TRACKING_DOMAIN}/track/click/{token}"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.5; color: #000;">
        <p>Chào bạn,</p>
        <p>Tôi thấy hôm qua bạn có tải app Tool Tài Xỉu nhưng chưa thấy bạn kích hoạt sử dụng phần mềm. Không biết bạn có gặp lỗi gì ở bước cài đặt không?</p>
        <p>Nếu bạn cần hỗ trợ cài đặt hoặc lấy mã kích hoạt, bạn cứ nhắn qua Bot Telegram của tôi ở link này nhé: <a href="{click_url}">Tại đây</a></p>
        <p>Hoặc nếu bị lỗi gì cứ Reply lại email này cho tôi nha.</p>
        <p>Cảm ơn bạn,</p>
        <p>Hỗ trợ kỹ thuật</p>
        <!-- Tracking Pixel -->
        <img src="{open_pixel_url}" width="1" height="1" style="display:none;" />
    </body>
    </html>
    """
    return html

def create_email_text(token: str) -> str:
    TRACKING_DOMAIN = "http://54.254.130.124"
    click_url = f"{TRACKING_DOMAIN}/track/click/{token}"

    text = f"""Chào bạn,

Tôi thấy hôm qua bạn có tải app Tool Tài Xỉu nhưng chưa thấy bạn kích hoạt sử dụng phần mềm. Không biết bạn có gặp lỗi gì ở bước cài đặt không?

Nếu bạn cần hỗ trợ cài đặt hoặc lấy mã kích hoạt, bạn cứ nhắn qua Bot Telegram của tôi ở link này nhé: {click_url}

Hoặc nếu bị lỗi gì cứ Reply lại email này cho tôi nha.

Cảm ơn bạn,
Hỗ trợ kỹ thuật
"""
def send_email(to_address: str, token: str):
    if not ses_client:
        logging.error("SES client is not initialized. Skipping send.")
        return False

    subject = "Lỗi cài đặt app hôm qua?"
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
