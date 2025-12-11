#!/usr/bin/env python3
"""Manual Instagram login helper - Import session from browser cookies."""

import sys
import json
from pathlib import Path

# Add project to path
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir))

import config
from instagrapi import Client
from instagrapi.exceptions import LoginRequired

print("""
\033[1;36m╔══════════════════════════════════════════════════════════════╗
║         Instagram Manual Login - Browser Session Import      ║
╚══════════════════════════════════════════════════════════════╝\033[0m

This script helps you import Instagram session from your browser
to bypass IP blocks and 2FA issues.

\033[1;33mSteps:\033[0m
1. Open Instagram in your browser (Chrome/Firefox)
2. Login normally (with 2FA if needed)
3. Open Developer Tools (F12)
4. Go to Application/Storage tab
5. Find 'Cookies' > 'instagram.com'
6. Copy the following cookie values:

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

print("\n" + "="*60)
print("\n\033[1;33m⏳ Creating session...\033[0m\n")

try:
    # Create client
    cl = Client()
    
    # Build settings dictionary with the correct structure for instagrapi
    settings = {
        "uuids": {
            "phone_id": cl.phone_id,
            "uuid": cl.uuid,
            "client_session_id": cl.client_session_id,
            "advertising_id": cl.advertising_id,
            "device_id": cl.device_id
        },
        "cookies": {},
        "last_login": None,
        "device_settings": cl.device_settings,
        "user_agent": cl.user_agent
    }
    
    # Add cookies
    settings["cookies"]["sessionid"] = sessionid
    settings["cookies"]["csrftoken"] = csrftoken
    settings["cookies"]["ds_user_id"] = ds_user_id
    
    # Set user_id
    cl.user_id = ds_user_id
    
    # Load settings
    cl.set_settings(settings)
    cl.set_user_agent(settings["user_agent"])
    
    # Build cookie jar
    for key, value in settings["cookies"].items():
        cl.set_cookie(key, value)
    
    # Test the session
    print("\033[1;33m🔍 Testing session...\033[0m")
    user_info = cl.account_info()
    
    print(f"\n\033[0;32m✅ Session valid!\033[0m")
    print(f"\033[0;32m✅ Logged in as: @{user_info.username}\033[0m")
    print(f"\033[0;32m✅ User ID: {user_info.pk}\033[0m")
    
    # Save session
    session_file = config.SESSION_DIR / f"{config.INSTAGRAM_USERNAME}_session.json"
    cl.dump_settings(session_file)
    
    print(f"\n\033[0;32m✅ Session saved to: {session_file}\033[0m")
    print("\n\033[1;32m╔══════════════════════════════════════════════════════════════╗")
    print("║                      ✅ SUCCESS!                              ║")
    print("╚══════════════════════════════════════════════════════════════╝\033[0m\n")
    print("You can now start the bot: \033[1;33mbash scripts/run.sh\033[0m\n")
    
except LoginRequired:
    print("\n\033[0;31m✗ Session invalid or expired!\033[0m")
    print("\033[1;33mTroubleshooting:\033[0m")
    print("1. Make sure you copied the complete cookie values")
    print("2. Login again in browser and get fresh cookies")
    print("3. Use Incognito/Private mode in browser")
    print("4. Clear browser cookies and login again\n")
    sys.exit(1)
    
except Exception as e:
    print(f"\n\033[0;31m✗ Error: {str(e)}\033[0m")
    print("\n\033[1;33m🔧 Troubleshooting:\033[0m")
    print("1. Make sure cookies are from a fresh login")
    print("2. Check that Instagram is still logged in your browser")
    print("3. Try copying cookies again")
    print("4. Make sure ds_user_id is only numbers\n")
    sys.exit(1)
