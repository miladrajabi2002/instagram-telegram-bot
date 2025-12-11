#!/usr/bin/env python3
"""Test Instagram connectivity and IP status."""

import sys
import requests
from pathlib import Path

# Add project to path
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir))

print("\n" + "="*60)
print("Instagram Connection & IP Test")
print("="*60 + "\n")

# Test 1: Basic internet connectivity
print("[1/5] Testing internet connection...")
try:
    response = requests.get('https://www.google.com', timeout=5)
    if response.status_code == 200:
        print("✅ Internet connection OK\n")
    else:
        print("❌ Internet connection failed\n")
        sys.exit(1)
except Exception as e:
    print(f"❌ Internet connection failed: {e}\n")
    sys.exit(1)

# Test 2: Check your public IP
print("[2/5] Checking your public IP address...")
try:
    response = requests.get('https://api.ipify.org?format=json', timeout=5)
    ip_data = response.json()
    public_ip = ip_data.get('ip', 'Unknown')
    print(f"✅ Your public IP: {public_ip}\n")
except Exception as e:
    print(f"⚠️ Could not detect IP: {e}\n")

# Test 3: Check if Instagram is accessible
print("[3/5] Testing Instagram website accessibility...")
try:
    response = requests.get('https://www.instagram.com', timeout=10)
    if response.status_code == 200:
        print("✅ Instagram website accessible\n")
    else:
        print(f"⚠️ Instagram returned status code: {response.status_code}\n")
except Exception as e:
    print(f"❌ Cannot reach Instagram: {e}\n")
    sys.exit(1)

# Test 4: Check Instagram API endpoint
print("[4/5] Testing Instagram API endpoint...")
try:
    headers = {
        'User-Agent': 'Instagram 269.0.0.18.75 Android (30/11; 420dpi; 1080x2340; OnePlus; 6T Dev; devitron; qcom; en_US; 314665256)'
    }
    response = requests.get(
        'https://i.instagram.com/api/v1/accounts/login/',
        headers=headers,
        timeout=10
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 405:
        print("✅ API endpoint accessible (405 is expected for GET request)\n")
    elif response.status_code == 403:
        print("❌ 403 Forbidden - Your IP is likely BLOCKED by Instagram\n")
    elif response.status_code == 429:
        print("❌ 429 Too Many Requests - Rate limited\n")
    else:
        print(f"⚠️ Unexpected response: {response.status_code}\n")
        
except Exception as e:
    print(f"❌ API test failed: {e}\n")

# Test 5: Try a simple Instagram API call
print("[5/5] Testing Instagram login endpoint (POST)...")
try:
    from instagrapi import Client
    
    cl = Client()
    
    # Try a fake login to see the response
    try:
        cl.login("test_fake_user_12345", "fake_password_67890")
    except Exception as e:
        error_msg = str(e)
        
        if '403' in error_msg or 'Forbidden' in error_msg:
            print("❌ 403 Forbidden - IP is BLOCKED")
            print("\n" + "="*60)
            print("DIAGNOSIS: Your server IP is blocked by Instagram")
            print("="*60)
            print("\nThis happens when:")
            print("  • Server/VPS IPs are commonly blocked")
            print("  • Too many automation attempts from same IP")
            print("  • Instagram detected non-human behavior")
            print("\n\033[1;33mSOLUTION:\033[0m")
            print("  Run: \033[1;32mbash scripts/login_alternative.sh\033[0m")
            print("  Choose option 1 (Import from browser)\n")
            
        elif 'user' in error_msg.lower() or 'password' in error_msg.lower():
            print("✅ Login endpoint is accessible (wrong credentials is expected)")
            print("\n" + "="*60)
            print("DIAGNOSIS: Connection is OK, not IP blocked")
            print("="*60)
            print("\nYour IP can reach Instagram API.")
            print("The login issue might be:")
            print("  • Wrong username/password in .env")
            print("  • 2FA not handled properly")
            print("  • Temporary Instagram issue")
            print("\n\033[1;33mSOLUTION:\033[0m")
            print("  1. Check credentials in .env")
            print("  2. Run: \033[1;32mbash scripts/login.sh\033[0m")
            print("  3. Enter 2FA code when prompted\n")
            
        else:
            print(f"⚠️ Unexpected error: {error_msg}")
            print("\nRun: bash scripts/login.sh and check the error\n")
            
except ImportError:
    print("❌ instagrapi not installed")
    print("Run: pip install instagrapi\n")

print("="*60)
print("Test completed")
print("="*60 + "\n")
