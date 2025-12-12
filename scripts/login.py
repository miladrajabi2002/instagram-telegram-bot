#!/usr/bin/env python3
"""Instagram Login Script with 2FA Support."""

import sys
from pathlib import Path

# Add project to path
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir))

import config
from instagrapi import Client
from instagrapi.exceptions import (
    TwoFactorRequired, ChallengeRequired,
    BadPassword, PleaseWaitFewMinutes,
    ClientError
)

print("\n" + "="*60)
print("Instagram Login")
print("="*60 + "\n")

if not config.INSTAGRAM_USERNAME or not config.INSTAGRAM_PASSWORD:
    print("❌ Error: Credentials not found in .env file")
    print("\nMake sure you have set:")
    print("  INSTAGRAM_USERNAME=your_username")
    print("  INSTAGRAM_PASSWORD=your_password\n")
    sys.exit(1)

print(f"Username: {config.INSTAGRAM_USERNAME}")
print("\n⏳ Connecting to Instagram...\n")

cl = Client()
cl.delay_range = [1, 3]

try:
    # First attempt - login without 2FA
    print("Attempting login...")
    cl.login(config.INSTAGRAM_USERNAME, config.INSTAGRAM_PASSWORD)
    
    # If we reach here, login was successful
    print("\n✅ Login successful!")
    
    # Save session
    session_file = config.SESSION_DIR / f"{config.INSTAGRAM_USERNAME}_session.json"
    cl.dump_settings(session_file)
    
    print(f"✅ Session saved: {session_file}")
    print(f"✅ User ID: {cl.user_id}")
    print("\n" + "="*60)
    print("✅ SUCCESS! You can now run: bash scripts/run.sh")
    print("="*60 + "\n")
    sys.exit(0)

except TwoFactorRequired:
    # 2FA is required
    print("\n⚠️  Two-Factor Authentication Required")
    print("\nCheck your phone for the 6-digit code.")
    print("Code usually arrives via SMS or Authenticator App.\n")
    
    # Get code from user
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            code = input(f"Enter 2FA code (attempt {attempt + 1}/{max_attempts}): ").strip()
            
            if not code:
                print("❌ Code cannot be empty\n")
                continue
            
            if len(code) != 6 or not code.isdigit():
                print("❌ Code must be exactly 6 digits\n")
                continue
            
            # Try login with 2FA code
            print("\n⏳ Verifying code...")
            cl.login(
                config.INSTAGRAM_USERNAME,
                config.INSTAGRAM_PASSWORD,
                verification_code=code
            )
            
            # Success!
            print("✅ 2FA verification successful!")
            
            # Save session
            session_file = config.SESSION_DIR / f"{config.INSTAGRAM_USERNAME}_session.json"
            cl.dump_settings(session_file)
            
            print(f"✅ Session saved: {session_file}")
            print(f"✅ User ID: {cl.user_id}")
            print("\n" + "="*60)
            print("✅ SUCCESS! You can now run: bash scripts/run.sh")
            print("="*60 + "\n")
            sys.exit(0)
            
        except ClientError as e:
            error_msg = str(e)
            if 'code is invalid' in error_msg.lower() or 'challenge' in error_msg.lower():
                print(f"❌ Invalid code. Try again.\n")
                if attempt < max_attempts - 1:
                    print("Make sure you're entering the latest code.")
                    print("Codes expire after 30 seconds.\n")
            else:
                print(f"❌ Error: {error_msg}\n")
                
        except Exception as e:
            print(f"❌ Verification error: {str(e)}\n")
    
    print("❌ Maximum attempts reached. Please try again later.")
    print("Run: python3 scripts/login.py\n")
    sys.exit(1)

except BadPassword:
    print("❌ Wrong password!")
    print("\nCheck INSTAGRAM_PASSWORD in your .env file.")
    print("Edit: nano .env\n")
    sys.exit(1)

except PleaseWaitFewMinutes:
    print("❌ Instagram rate limit!")
    print("\nInstagram is asking you to wait.")
    print("Wait 15-30 minutes and try again.")
    print("Use Instagram app normally during the wait.\n")
    sys.exit(1)

except ChallengeRequired as e:
    print("❌ Security challenge required!")
    print("\nInstagram needs additional verification.")
    print("\nSteps to resolve:")
    print("  1. Open Instagram app on your phone")
    print("  2. Complete any security checks shown")
    print("  3. Wait 5-10 minutes")
    print("  4. Try again: python3 scripts/login.py\n")
    print(f"Details: {str(e)}\n")
    sys.exit(1)

except Exception as e:
    error_str = str(e)
    
    if '403' in error_str or 'forbidden' in error_str or 'problem with your request' in error_str:
        print("❌ IP Blocked (403 Forbidden)")
        print("\nYour server IP is blocked by Instagram.")
        print("This is common with VPS/server IPs.")
        print("\n✨ Solution: Import session from browser")
        print("\nRun: bash scripts/login_alternative.sh")
        print("Choose option 1 (Import from browser cookies)\n")
    else:
        print(f"❌ Login failed: {error_str}")
        print("\nIf the error persists:")
        print("  1. Check your credentials in .env")
        print("  2. Make sure Instagram account is not locked")
        print("  3. Try logging in via Instagram app first")
        print("  4. Check logs: tail -f logs/bot.log\n")
    
    sys.exit(1)
