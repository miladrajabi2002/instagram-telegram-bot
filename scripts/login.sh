#!/bin/bash
# Standalone Instagram Login Script with 2FA Support

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Create login script
cat > /tmp/instagram_login.py << 'PYEOF'
import sys
import os
from pathlib import Path

# Add project to path
project_dir = Path(os.getcwd())
sys.path.insert(0, str(project_dir))

import config
from core.insta_client import InstagramClient
from includes.logger import setup_logger

logger = setup_logger(__name__)

def main():
    print("\n🔐 Logging in to Instagram...\n")
    
    # Check credentials
    if not config.INSTAGRAM_USERNAME or not config.INSTAGRAM_PASSWORD:
        print("\033[0;31m❌ Instagram credentials not found in .env file!\033[0m")
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
        success = client.login()
        
        if success:
            print("\n\033[0;32m✅ Login successful!\033[0m")
            print(f"\033[0;32m✅ Session saved to: {client.session_file}\033[0m\n")
            
            # Test API call
            print("Testing Instagram API...")
            user_id = client.get_my_user_id()
            if user_id:
                print(f"\033[0;32m✅ Your Instagram User ID: {user_id}\033[0m\n")
            
            return True
        else:
            # 2FA required
            print("\n\033[1;33m⚠️  Two-Factor Authentication Required\033[0m\n")
            
            max_attempts = 3
            for attempt in range(max_attempts):
                code = input(f"Enter 2FA code (attempt {attempt + 1}/{max_attempts}): ").strip()
                
                if not code:
                    print("\033[0;31m❌ Code cannot be empty\033[0m")
                    continue
                
                if client.verify_2fa(code):
                    print("\n\033[0;32m✅ 2FA verification successful!\033[0m")
                    print(f"\033[0;32m✅ Session saved to: {client.session_file}\033[0m\n")
                    
                    # Test API call
                    print("Testing Instagram API...")
                    user_id = client.get_my_user_id()
                    if user_id:
                        print(f"\033[0;32m✅ Your Instagram User ID: {user_id}\033[0m\n")
                    
                    return True
                else:
                    print("\033[0;31m❌ Invalid code, please try again\033[0m\n")
            
            print("\033[0;31m❌ Max attempts reached. Login failed.\033[0m")
            return False
            
    except Exception as e:
        print(f"\n\033[0;31m❌ Login error: {str(e)}\033[0m\n")
        
        # Provide troubleshooting
        print("\033[1;33m🔧 Troubleshooting:\033[0m")
        print("1. Check your username and password in .env file")
        print("2. If you have 2FA enabled, you'll be prompted for the code")
        print("3. If challenge required, verify your account in Instagram app first")
        print("4. Try again after a few minutes if rate limited")
        print("5. Check logs: cat logs/bot.log")
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
    echo -e "${YELLOW}Please fix the issues above and try again:${NC}"
    echo -e "  bash scripts/login.sh"
    echo ""
    exit 1
fi
