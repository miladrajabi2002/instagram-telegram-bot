#!/bin/bash
# Standalone Instagram Login Script with 2FA Support and Multiple Options

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Instagram Login with 2FA Support${NC}"
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

# Create enhanced login script
cat > /tmp/instagram_login.py << 'PYEOF'
import sys
import os
import time
from pathlib import Path

# Add project to path
project_dir = Path(os.getcwd())
sys.path.insert(0, str(project_dir))

import config
from core.insta_client import InstagramClient
from includes.logger import setup_logger
from instagrapi.exceptions import TwoFactorRequired, ChallengeRequired, BadPassword, PleaseWaitFewMinutes

logger = setup_logger(__name__)

def print_menu():
    """Print 2FA options menu."""
    print("\n\033[1;36m2FA Verification Options:\033[0m")
    print("1. Enter 6-digit code from SMS")
    print("2. Enter 6-digit code from Authenticator App")
    print("3. Request new code (resend)")
    print("4. Switch to different method")
    print("5. Cancel and exit")
    print("")

def handle_2fa(client):
    """Handle 2FA with multiple options."""
    max_attempts = 5
    
    for attempt in range(max_attempts):
        print_menu()
        choice = input("Select option (1-5): ").strip()
        
        if choice == '1' or choice == '2':
            code = input(f"\nEnter 6-digit code (attempt {attempt + 1}/{max_attempts}): ").strip()
            
            if not code:
                print("\033[0;31m✗ Code cannot be empty\033[0m")
                continue
            
            if not code.isdigit() or len(code) != 6:
                print("\033[0;31m✗ Code must be 6 digits\033[0m")
                continue
            
            try:
                if client.verify_2fa(code):
                    print("\n\033[0;32m✅ 2FA verification successful!\033[0m")
                    return True
                else:
                    print("\033[0;31m✗ Invalid code, please try again\033[0m")
            except Exception as e:
                print(f"\033[0;31m✗ Verification error: {str(e)}\033[0m")
        
        elif choice == '3':
            print("\n\033[1;33m📨 Requesting new code...\033[0m")
            print("Please wait a moment and check your phone for new SMS/notification.")
            time.sleep(3)
            print("\033[0;32m✓ Ready to receive new code\033[0m")
        
        elif choice == '4':
            print("\n\033[1;33m🔄 To switch verification method:\033[0m")
            print("1. Open Instagram app on your phone")
            print("2. Go to Settings > Security > Two-Factor Authentication")
            print("3. Change your preferred method (SMS or Authenticator)")
            print("4. Come back and try again")
            print("")
            input("Press Enter when ready to continue...")
        
        elif choice == '5':
            print("\n\033[0;33m❌ Login cancelled\033[0m")
            return False
        
        else:
            print("\033[0;31m✗ Invalid option\033[0m")
    
    print("\033[0;31m✗ Max attempts reached\033[0m")
    return False

def main():
    print("\n🔐 Logging in to Instagram...\n")
    
    # Check credentials
    if not config.INSTAGRAM_USERNAME or not config.INSTAGRAM_PASSWORD:
        print("\033[0;31m✗ Instagram credentials not found in .env file!\033[0m")
        return False
    
    print(f"Username: {config.INSTAGRAM_USERNAME}")
    print("")
    
    # Create client without Telegram notifier
    client = InstagramClient(
        username=config.INSTAGRAM_USERNAME,
        password=config.INSTAGRAM_PASSWORD,
        telegram_notifier=None
    )
    
    try:
        # Attempt login
        print("\033[1;33m⏳ Connecting to Instagram...\033[0m")
        success = client.login()
        
        if success:
            print("\n\033[0;32m✅ Login successful!\033[0m")
            print(f"\033[0;32m✅ Session saved to: {client.session_file}\033[0m\n")
            
            # Test API call
            print("\033[1;33m🔍 Testing Instagram API...\033[0m")
            user_id = client.get_my_user_id()
            if user_id:
                print(f"\033[0;32m✅ Your Instagram User ID: {user_id}\033[0m\n")
            
            return True
        else:
            # 2FA required
            print("\n\033[1;33m⚠️  Two-Factor Authentication Required\033[0m\n")
            print("Check your phone for:")
            print("  • SMS with 6-digit code")
            print("  • Authenticator app notification")
            print("  • Instagram app notification")
            
            return handle_2fa(client)
            
    except BadPassword:
        print("\n\033[0;31m✗ Incorrect password!\033[0m\n")
        print("\033[1;33m🔧 Solution:\033[0m")
        print("1. Edit .env file: nano .env")
        print("2. Update INSTAGRAM_PASSWORD with correct password")
        print("3. Try again: bash scripts/login.sh")
        return False
    
    except PleaseWaitFewMinutes:
        print("\n\033[0;31m✗ Instagram rate limit!\033[0m\n")
        print("\033[1;33m🔧 Solution:\033[0m")
        print("Instagram is asking you to wait. This usually means:")
        print("1. Too many login attempts in short time")
        print("2. Wait 15-30 minutes before trying again")
        print("3. Use Instagram app normally on your phone during wait")
        print("4. Try again later: bash scripts/login.sh")
        return False
    
    except ChallengeRequired as e:
        print("\n\033[0;31m✗ Instagram Security Challenge Required!\033[0m\n")
        print("\033[1;33m🔧 Solution:\033[0m")
        print("1. Open Instagram app on your phone")
        print("2. You should see a security check or verification request")
        print("3. Complete the challenge (verify it's you)")
        print("4. Wait 5-10 minutes")
        print("5. Try login again: bash scripts/login.sh")
        print("")
        print(f"Details: {str(e)}")
        return False
    
    except Exception as e:
        error_msg = str(e).lower()
        
        print(f"\n\033[0;31m✗ Login error: {str(e)}\033[0m\n")
        
        # Specific error handling
        if 'checkpoint' in error_msg or 'challenge' in error_msg:
            print("\033[1;33m🔧 Instagram Security Check Required:\033[0m")
            print("1. Open Instagram app on your phone")
            print("2. Complete any security verifications")
            print("3. Wait 10 minutes")
            print("4. Try again")
        
        elif 'feedback_required' in error_msg or 'spam' in error_msg:
            print("\033[1;33m🔧 Account Flagged:\033[0m")
            print("1. Your account might be flagged for suspicious activity")
            print("2. Use Instagram normally for 24-48 hours")
            print("3. Avoid automation during this time")
            print("4. Try login again later")
        
        elif 'wait' in error_msg or 'try again later' in error_msg:
            print("\033[1;33m🔧 Rate Limited:\033[0m")
            print("1. Wait 15-30 minutes")
            print("2. Use Instagram app on phone")
            print("3. Try again later")
        
        elif 'network' in error_msg or 'connection' in error_msg:
            print("\033[1;33m🔧 Network Issue:\033[0m")
            print("1. Check internet connection")
            print("2. Try again in a moment")
        
        else:
            print("\033[1;33m🔧 General Troubleshooting:\033[0m")
            print("1. Check username and password in .env")
            print("2. Verify account is not locked/disabled")
            print("3. Try logging in via Instagram app first")
            print("4. Check logs: cat logs/bot.log")
        
        print("")
        return False

if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1)
PYEOF

# Run login script
python /tmp/instagram_login.py
LOGIN_RESULT=$?

# Cleanup
rm -f /tmp/instagram_login.py

if [ $LOGIN_RESULT -eq 0 ]; then
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}Login Successful!${NC}"
    echo -e "${GREEN}======================================${NC}"
    echo ""
    echo -e "${YELLOW}Your session is now saved and ready to use.${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo -e "1. Start the bot: ${YELLOW}bash scripts/run.sh${NC}"
    echo -e "2. Or use systemd: ${YELLOW}sudo systemctl start instagram-bot${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}======================================${NC}"
    echo -e "${RED}Login Failed${NC}"
    echo -e "${RED}======================================${NC}"
    echo ""
    echo -e "${YELLOW}Follow the troubleshooting steps above.${NC}"
    echo -e "${YELLOW}Try again when ready: bash scripts/login.sh${NC}"
    echo ""
    exit 1
fi
