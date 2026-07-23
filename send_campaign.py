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

def create_email_html(token: str, drip_stage: int) -> str:
    TRACKING_DOMAIN = "http://54.254.130.124"
    open_pixel_url = f"{TRACKING_DOMAIN}/track/open/{token}.gif"
    click_url = f"{TRACKING_DOMAIN}/track/click/{token}"

    if drip_stage == 1:
        body_content = f"""
        <p>Chào bạn,</p>
        <p>Tôi thấy hôm qua bạn có tải app Tool Tài Xỉu nhưng chưa thấy bạn kích hoạt sử dụng phần mềm. Không biết bạn có gặp lỗi gì ở bước cài đặt không?</p>
        <p>Nếu bạn cần hỗ trợ cài đặt hoặc lấy mã kích hoạt, bạn cứ nhắn qua Bot Telegram của tôi ở link này nhé: <a href="{click_url}">Tại đây</a></p>
        <p>Hoặc nếu bị lỗi gì cứ Reply lại email này cho tôi nha.</p>
        <p>Cảm ơn bạn,</p>
        <p>Hỗ trợ kỹ thuật</p>
        """
    elif drip_stage == 2:
        body_content = f"""
        <p>Chào bạn, tôi thấy hệ thống báo bạn chưa nhận mã chuyển đổi sang App AI mới.</p>
        <p>Tối qua hệ thống AI phân tích thực tế trên Google Play đã có những nhịp rất chuẩn. Vì số lượng mã VIP 30 ngày có hạn, nếu đến tối nay bạn chưa lấy mã trong Bot Telegram, hệ thống sẽ tự động nhường mã này cho thành viên khác.</p>
        <p>Bạn vào đây lấy mã ngay để giữ chỗ nhé: <a href="{click_url}">Tại đây</a></p>
        <p>Cảm ơn bạn,</p>
        """
    else:
        body_content = f"""
        <p>Chào bạn, vì bạn không phản hồi nên hệ thống sẽ tiến hành hủy mã VIP nâng cấp bản AI của bạn vào 12h đêm nay.</p>
        <p>Đây là email cuối cùng hỗ trợ bạn chuyển đổi. Từ ngày mai, bạn sẽ phải tải app trực tiếp và không còn được cấp mã VIP 30 ngày nữa.</p>
        <p>Nếu bạn thay đổi ý định, hãy nhắn cho Bot hỗ trợ trước 12h đêm: <a href="{click_url}">Tại đây</a></p>
        <p>Chào bạn,</p>
        """

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.5; color: #000;">
        {body_content}
        <!-- Tracking Pixel -->
        <img src="{open_pixel_url}" width="1" height="1" style="display:none;" />
    </body>
    </html>
    """
    return html

def create_email_text(token: str, drip_stage: int) -> str:
    TRACKING_DOMAIN = "http://54.254.130.124"
    click_url = f"{TRACKING_DOMAIN}/track/click/{token}"

    if drip_stage == 1:
        text = f"""Chào bạn,

Tôi thấy hôm qua bạn có tải app Tool Tài Xỉu nhưng chưa thấy bạn kích hoạt sử dụng phần mềm. Không biết bạn có gặp lỗi gì ở bước cài đặt không?

Nếu bạn cần hỗ trợ cài đặt hoặc lấy mã kích hoạt, bạn cứ nhắn qua Bot Telegram của tôi ở link này nhé: {click_url}

Hoặc nếu bị lỗi gì cứ Reply lại email này cho tôi nha.

Cảm ơn bạn,
Hỗ trợ kỹ thuật"""
    elif drip_stage == 2:
        text = f"""Chào bạn, tôi thấy hệ thống báo bạn chưa nhận mã chuyển đổi sang App AI mới.

Tối qua hệ thống AI phân tích thực tế trên Google Play đã có những nhịp rất chuẩn. Vì số lượng mã VIP 30 ngày có hạn, nếu đến tối nay bạn chưa lấy mã trong Bot Telegram, hệ thống sẽ tự động nhường mã này cho thành viên khác.

Bạn vào đây lấy mã ngay để giữ chỗ nhé: {click_url}

Cảm ơn bạn,"""
    else:
        text = f"""Chào bạn, vì bạn không phản hồi nên hệ thống sẽ tiến hành hủy mã VIP nâng cấp bản AI của bạn vào 12h đêm nay.

Đây là email cuối cùng hỗ trợ bạn chuyển đổi. Từ ngày mai, bạn sẽ phải tải app trực tiếp và không còn được cấp mã VIP 30 ngày nữa.

Nếu bạn thay đổi ý định, hãy nhắn cho Bot hỗ trợ trước 12h đêm: {click_url}

Chào bạn,"""
    return text

def send_email(to_address: str, token: str, drip_stage: int):
    if not ses_client:
        logging.error("SES client is not initialized. Skipping send.")
        return False, False

    if drip_stage == 1:
        subject = "Lỗi cài đặt app hôm qua?"
    elif drip_stage == 2:
        subject = "Trạng thái mã VIP của bạn (Chưa kích hoạt)"
    else:
        subject = "Thông báo hủy mã phiên bản mới"

    html_body = create_email_html(token, drip_stage)
    text_body = create_email_text(token, drip_stage)

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
