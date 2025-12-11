#!/usr/bin/env python3
"""Simple direct login without 2FA complications."""

import sys
from pathlib import Path
import time

# Add project to path
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir))

import config
from instagrapi import Client
from instagrapi.exceptions import (
    TwoFactorRequired, ChallengeRequired, 
    BadPassword, PleaseWaitFewMinutes
)

print("\n" + "="*60)
print("Instagram Login - Simplified")
print("="*60 + "\n")

if not config.INSTAGRAM_USERNAME or not config.INSTAGRAM_PASSWORD:
    print("\033[0;31m✗ Credentials not found in .env\033[0m")
    sys.exit(1)

print(f"Username: {config.INSTAGRAM_USERNAME}")
print("\n⏳ Attempting login...\n")

cl = Client()
cl.delay_range = [1, 3]

try:
    # Try login
    cl.login(config.INSTAGRAM_USERNAME, config.INSTAGRAM_PASSWORD)
    
    # If we get here, login succeeded
    print("\033[0;32m✅ Login successful!\033[0m")
    
    # Save session
    session_file = config.SESSION_DIR / f"{config.INSTAGRAM_USERNAME}_session.json"
    cl.dump_settings(session_file)
    
    print(f"\033[0;32m✅ Session saved: {session_file}\033[0m")
    
    # Test
    user_id = cl.user_id
    print(f"\033[0;32m✅ User ID: {user_id}\033[0m\n")
    
except TwoFactorRequired:
    print("\033[1;33m⚠️  2FA Required\033[0m\n")
    
    # Get 2FA code
    for attempt in range(3):
        code = input(f"Enter 6-digit code (attempt {attempt+1}/3): ").strip()
        
        if len(code) != 6 or not code.isdigit():
            print("\033[0;31m✗ Code must be 6 digits\033[0m")
            continue
        
        try:
            # Try verification
            cl.login(config.INSTAGRAM_USERNAME, config.INSTAGRAM_PASSWORD, verification_code=code)
            
            print("\n\033[0;32m✅ 2FA successful!\033[0m")
            
            # Save session
            session_file = config.SESSION_DIR / f"{config.INSTAGRAM_USERNAME}_session.json"
            cl.dump_settings(session_file)
            
            print(f"\033[0;32m✅ Session saved: {session_file}\033[0m")
            print(f"\033[0;32m✅ User ID: {cl.user_id}\033[0m\n")
            
            sys.exit(0)
            
        except Exception as e:
            print(f"\033[0;31m✗ Invalid: {str(e)}\033[0m")
    
    print("\n\033[0;31m✗ Max attempts reached\033[0m\n")
    sys.exit(1)

except BadPassword:
    print("\033[0;31m✗ Wrong password!\033[0m")
    print("Check INSTAGRAM_PASSWORD in .env\n")
    sys.exit(1)

except PleaseWaitFewMinutes:
    print("\033[0;31m✗ Rate limited!\033[0m")
    print("Wait 15-30 minutes and try again\n")
    sys.exit(1)

except ChallengeRequired as e:
    print("\033[0;31m✗ Challenge required!\033[0m")
    print("Complete security check in Instagram app first\n")
    print(f"Details: {e}\n")
    sys.exit(1)

except Exception as e:
    error_str = str(e).lower()
    
    if '403' in error_str or 'forbidden' in error_str:
        print("\033[0;31m✗ IP Blocked (403)\033[0m\n")
        print("\033[1;33m🔧 Solution: Use alternative login method\033[0m")
        print("Run: \033[1;32mbash scripts/login_alternative.sh\033[0m")
        print("Choose option 1 to import from browser\n")
    else:
        print(f"\033[0;31m✗ Error: {str(e)}\033[0m\n")
    
    sys.exit(1)
