#!/bin/bash
# Simple Instagram Login with 2FA support

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Instagram Login${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo -e "${YELLOW}Run setup first: bash setup.sh${NC}"
    exit 1
fi

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo -e "${YELLOW}Run setup first: bash setup.sh${NC}"
    exit 1
fi

source venv/bin/activate

# Create temporary Python script
cat > /tmp/instagram_login_$$.py << 'PYEOF'
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path.cwd()))

import config
from instagrapi import Client
from instagrapi.exceptions import (
    TwoFactorRequired, ChallengeRequired,
    BadPassword, PleaseWaitFewMinutes
)

print(f"Username: {config.INSTAGRAM_USERNAME}")
print("\n⏳ Connecting to Instagram...\n")

cl = Client()
cl.delay_range = [1, 3]

try:
    # First attempt - try without 2FA
    print("Attempting login...")
    cl.login(config.INSTAGRAM_USERNAME, config.INSTAGRAM_PASSWORD)
    
    # If successful
    print("\n✅ Login successful!")
    
    # Save session
    session_file = config.SESSION_DIR / f"{config.INSTAGRAM_USERNAME}_session.json"
    cl.dump_settings(session_file)
    
    print(f"✅ Session saved: {session_file}")
    print(f"✅ User ID: {cl.user_id}")
    print("\n" + "="*60)
    print("SUCCESS! You can now run: bash scripts/run.sh")
    print("="*60 + "\n")
    sys.exit(0)
    
except TwoFactorRequired:
    print("\n⚠️  Two-Factor Authentication Required")
    print("\nCheck your phone for the 6-digit code.\n")
    # Exit with special code to indicate 2FA needed
    sys.exit(10)

except BadPassword:
    print("\n❌ Wrong password!")
    print("Check INSTAGRAM_PASSWORD in .env file\n")
    sys.exit(1)

except PleaseWaitFewMinutes:
    print("\n❌ Rate limited by Instagram")
    print("Wait 15-30 minutes and try again\n")
    sys.exit(1)

except ChallengeRequired as e:
    print("\n❌ Security challenge required")
    print("Complete the security check in Instagram app first")
    print(f"Details: {str(e)}\n")
    sys.exit(1)

except Exception as e:
    error_str = str(e)
    
    if '403' in error_str or 'forbidden' in error_str:
        print("\n❌ IP Blocked (403 Forbidden)")
        print("\nYour server IP is blocked by Instagram.")
        print("\nSolution: Use alternative login method")
        print("Run: bash scripts/login_alternative.sh")
        print("Choose option 1 (browser cookies)\n")
    else:
        print(f"\n❌ Login failed: {str(e)}\n")
    
    sys.exit(1)
PYEOF

# Run initial login attempt
python3 /tmp/instagram_login_$$.py
LOGIN_RESULT=$?

# Check if 2FA is needed (exit code 10)
if [ $LOGIN_RESULT -eq 10 ]; then
    # Get 2FA code from user
    read -p "Enter 2FA code: " VERIFICATION_CODE
    
    if [ -z "$VERIFICATION_CODE" ]; then
        echo -e "${RED}\n❌ Code cannot be empty${NC}\n"
        rm -f /tmp/instagram_login_$$.py
        exit 1
    fi
    
    # Create 2FA login script
    cat > /tmp/instagram_login_2fa_$$.py << PYEOF
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

import config
from instagrapi import Client

print("\n⏳ Verifying 2FA code...\n")

cl = Client()
cl.delay_range = [1, 3]

try:
    # Login with verification code
    cl.login(
        config.INSTAGRAM_USERNAME,
        config.INSTAGRAM_PASSWORD,
        verification_code="${VERIFICATION_CODE}"
    )
    
    print("✅ 2FA verification successful!")
    
    # Save session
    session_file = config.SESSION_DIR / f"{config.INSTAGRAM_USERNAME}_session.json"
    cl.dump_settings(session_file)
    
    print(f"✅ Session saved: {session_file}")
    print(f"✅ User ID: {cl.user_id}")
    print("\n" + "="*60)
    print("SUCCESS! You can now run: bash scripts/run.sh")
    print("="*60 + "\n")
    
except Exception as e:
    print(f"\n❌ Verification failed: {str(e)}")
    print("\nMake sure you entered the correct code.")
    print("Run again: bash scripts/login.sh\n")
    sys.exit(1)
PYEOF
    
    # Run 2FA verification
    python3 /tmp/instagram_login_2fa_$$.py
    LOGIN_RESULT=$?
    
    # Cleanup
    rm -f /tmp/instagram_login_2fa_$$.py
fi

# Cleanup
rm -f /tmp/instagram_login_$$.py

if [ $LOGIN_RESULT -eq 0 ]; then
    echo -e "${GREEN}Login completed successfully!${NC}"
    exit 0
else
    echo -e "${RED}Login failed. Check the error above.${NC}"
    exit 1
fi
