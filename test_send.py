import sys
import os
import boto3
from send_campaign import send_email

# Load environment variables (since this runs standalone)
# Environment variables are provided by docker-compose

TEST_EMAILS = [
    "ngothanhlamit@gmail.com",
    "ngolam11101993@gmail.com",
    "dtruong1119@gmail.com"
]

def run_test():
    print("=== STARTING SES TEST ===")
    success_count = 0
    for email in TEST_EMAILS:
        print(f"Sending test email to: {email}...")
        # Sử dụng 1 token giả để test tracking
        token = f"test_token_{email.split('@')[0]}"
        success = send_email(email, token)
        if success:
            print(f"✅ Gửi thành công tới {email}")
            success_count += 1
        else:
            print(f"❌ Thất bại khi gửi tới {email} (Xem lỗi bên trên)")
            
    print(f"=== TEST HOÀN TẤT: Thành công {success_count}/{len(TEST_EMAILS)} ===")

if __name__ == "__main__":
    run_test()
