import os
import sqlite3
import time
import logging
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import database as db

SENDER = "admin@tooltaixiu.org"
AWS_REGION = "ap-southeast-1"

try:
    ses_client = boto3.client('ses', region_name=AWS_REGION)
except Exception as e:
    logging.error(f"Failed to initialize SES client: {e}")
    ses_client = None

def send_email(to_address: str, token: str, drip_stage: int):
    if not ses_client:
        logging.error("SES client is not initialized. Skipping send.")
        return False, False

    template = db.get_template(drip_stage)
    if not template:
        logging.error(f"Template for stage {drip_stage} not found in DB.")
        return False, False

    subject = template['subject']
    sender_name = template['sender_name']
    
    # Render HTML Body
    TRACKING_DOMAIN = "http://54.254.130.124"
    open_pixel_url = f"{TRACKING_DOMAIN}/track/open/{token}.gif"
    click_url = f"{TRACKING_DOMAIN}/track/click/{token}"
    
    body_content = template['body_html'].replace("{click_url}", click_url)
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.5; color: #000;">
        {body_content}
        <!-- Tracking Pixel -->
        <img src="{open_pixel_url}" width="1" height="1" style="display:none;" />
    </body>
    </html>
    """
    
    # Strip basic tags for text body
    text_body = body_content.replace("<p>", "").replace("</p>", "\n\n").replace("<br>", "\n").replace("</a>", "")
    text_body = text_body.replace(f'<a href="{click_url}">Tại đây', click_url)
    text_body = text_body.replace(f'<a href="{click_url}">', click_url)

    # Format Sender Name with Default Email
    # Fallback to hardcoded admin email if SENDER is not properly formatted
    sender_email = "support@tooltaixiu.org" 
    formatted_sender = f"{sender_name} <{sender_email}>"

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
            Source=formatted_sender,
        )
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logging.error(f"SES ClientError to {to_address}: {error_code}")
        # MessageRejected or InvalidParameterValue usually means hard bounce / invalid email
        if error_code in ['MessageRejected', 'InvalidParameterValue', 'ConfigurationSetDoesNotExist']:
            return False, True # is_hard_error = True
        return False, False # is_hard_error = False
    except Exception as e:
        logging.error(f"Network/System error sending to {to_address}: {e}")
        return False, False # is_hard_error = False
    else:
        logging.info(f"Email sent to {to_address}! Message ID: {response['MessageId']}")
        return True, False

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
        drip_stage = row['drip_stage']

        success, is_hard = send_email(email, token, drip_stage)
        
        if not ses_client:
            logging.info(f"[SIMULATION] Sent email to {email} with token {token}")
            success = True

        if success:
            db.mark_sent(email_id, drip_stage)
        else:
            db.mark_failed(email_id, is_hard_error=is_hard)
        
        time.sleep(delay_seconds)

if __name__ == "__main__":
    db.init_db()
    run_campaign(batch_size=10, delay_seconds=1)
