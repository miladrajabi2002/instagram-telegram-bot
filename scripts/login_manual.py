#!/usr/bin/env python3
"""Manual Instagram login helper - Import session from browser cookies."""

import sys
import json
import uuid
from pathlib import Path

# Add project to path
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir))

import config
from instagrapi import Client

print("""
\033[1;36m╔══════════════════════════════════════════════════════════════╗
║         Instagram Manual Login - Browser Session Import      ║
╚══════════════════════════════════════════════════════════════╝\033[0m

This script helps you import Instagram session from your browser.

\033[1;33mSteps:\033[0m
1. Open Instagram in your browser (Chrome/Firefox)
2. Login normally (with 2FA if needed)
3. Press F12 to open Developer Tools
4. Go to 'Application' tab (Chrome) or 'Storage' tab (Firefox)
5. Click on 'Cookies' > 'https://www.instagram.com'
6. Find and copy these values:

""")

print("\033[1;32mRequired cookies:\033[0m")
print("  • sessionid")
print("  • csrftoken")
print("  • ds_user_id")
print("\n" + "="*60 + "\n")

# Get cookies from user
sessionid = input("Enter 'sessionid' cookie value: ").strip()
if not sessionid:
    print("\033[0;31m✗ sessionid is required!\033[0m")
    sys.exit(1)

csrftoken = input("Enter 'csrftoken' cookie value: ").strip()
if not csrftoken:
    print("\033[0;31m✗ csrftoken is required!\033[0m")
    sys.exit(1)

ds_user_id = input("Enter 'ds_user_id' cookie value: ").strip()
if not ds_user_id:
    print("\033[0;31m✗ ds_user_id is required!\033[0m")
    sys.exit(1)

if not ds_user_id.isdigit():
    print("\033[0;31m✗ ds_user_id must be only numbers!\033[0m")
    sys.exit(1)

print("\n" + "="*60)
print("\n\033[1;33m⏳ Creating session...\033[0m\n")

try:
    # Create a fresh client
    cl = Client()
    
    # Manually set the essential properties
    cl.user_id = ds_user_id
    
    # Get current settings structure
    current_settings = cl.get_settings()
    
    # Update cookies in settings
    current_settings['cookies'] = {
        'sessionid': sessionid,
        'csrftoken': csrftoken,
        'ds_user_id': ds_user_id,
    }
    
    # Load the modified settings
    cl.set_settings(current_settings)
    
    # Test the session by making an API call
    print("\033[1;33m🔍 Testing session...\033[0m")
    user_info = cl.account_info()
    
    print(f"\n\033[0;32m✅ Session is valid!\033[0m")
    print(f"\033[0;32m✅ Logged in as: @{user_info.username}\033[0m")
    print(f"\033[0;32m✅ Full name: {user_info.full_name}\033[0m")
    print(f"\033[0;32m✅ User ID: {user_info.pk}\033[0m")
    
    # Save session to file
    session_file = config.SESSION_DIR / f"{config.INSTAGRAM_USERNAME}_session.json"
    cl.dump_settings(session_file)
    
    print(f"\n\033[0;32m✅ Session saved to: {session_file}\033[0m")
    print("\n\033[1;32m╔══════════════════════════════════════════════════════════════╗")
    print("║                      ✅ SUCCESS!                              ║")
    print("╚══════════════════════════════════════════════════════════════╝\033[0m\n")
    print("You can now start the bot: \033[1;33mbash scripts/run.sh\033[0m\n")
    
    sys.exit(0)
    
except Exception as e:
    error_msg = str(e)
    print(f"\n\033[0;31m✗ Error: {error_msg}\033[0m")
    
    if 'login_required' in error_msg.lower():
        print("\n\033[1;33m🔧 Session is invalid or expired\033[0m")
        print("\n\033[1;33mTroubleshooting:\033[0m")
        print("1. Make sure you're logged in on Instagram website")
        print("2. Copy fresh cookies (logout and login again if needed)")
        print("3. Make sure you copied the FULL cookie values")
        print("4. Use Incognito/Private mode and login fresh\n")
    else:
        print("\n\033[1;33m🔧 Troubleshooting:\033[0m")
        print("1. Verify you copied complete cookie values (no spaces)")
        print("2. Make sure Instagram is still logged in your browser")
        print("3. Try in Incognito mode: login fresh and copy cookies again")
        print("4. Check ds_user_id is only numbers (no letters)\n")
    
    sys.exit(1)
