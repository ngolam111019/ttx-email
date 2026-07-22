import boto3
import subprocess
import os

ses = boto3.client('ses', region_name='ap-southeast-1')
domain = 'tooltaixiu.org'
print(f"=== AWS SES DKIM CHECK FOR {domain} (Singapore) ===")

try:
    response = ses.get_identity_dkim_attributes(Identities=[domain])
    if domain in response['DkimAttributes']:
        attrs = response['DkimAttributes'][domain]
        status = attrs.get('DkimVerificationStatus', 'Unknown')
        tokens = attrs.get('DkimTokens', [])
        print(f"Current AWS Status: {status}")
        
        print("\n=== THE EXACT RECORDS YOU NEED IN HOSTINGER ===")
        all_good = True
        for token in tokens:
            name = f"{token}._domainkey"
            value = f"{token}.dkim.amazonses.com"
            print(f"\nType: CNAME")
            print(f"Name/Host: {name}")
            print(f"Target/Value: {value}")
            
            full_domain = f"{name}.{domain}"
            try:
                result = subprocess.check_output(["dig", full_domain, "CNAME", "+short"]).decode('utf-8').strip()
                if value in result:
                    print(f"Status: ✅ SUCCESS - This record is correct and live!")
                else:
                    all_good = False
                    if result:
                        print(f"Status: ❌ FAILED - Currently resolving to wrong value: {result}")
                    else:
                        print(f"Status: ❌ FAILED - Missing. Not found on the internet.")
            except Exception as e:
                print(f"Status: ❌ ERROR checking DNS: {e}")
                
        if all_good and tokens:
            print("\n🎉 ALL RECORDS ARE CORRECT! AWS should verify it very soon.")
        else:
            print("\n⚠️ ACTION REQUIRED: Please fix the ❌ FAILED records in Hostinger.")
    else:
        print(f"Domain '{domain}' was not found in your AWS SES (us-east-1). Did you add it?")
except Exception as e:
    print(f"Error accessing AWS: {e}")
