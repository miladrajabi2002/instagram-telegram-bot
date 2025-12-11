#!/bin/bash
# Alternative login methods when standard login fails

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      Alternative Login Methods - Choose Your Option          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}If standard login (bash scripts/login.sh) is failing with 403${NC}"
echo -e "${YELLOW}error, Instagram may have blocked your server IP.${NC}"
echo ""
echo -e "${BLUE}Choose a method:${NC}"
echo ""
echo -e "${GREEN}1.${NC} Import session from browser cookies (RECOMMENDED)"
echo -e "   ${CYAN}→ Login via browser, copy cookies, works 100%${NC}"
echo ""
echo -e "${GREEN}2.${NC} Use proxy/VPN and retry login"
echo -e "   ${CYAN}→ Setup proxy in .env, then retry bash scripts/login.sh${NC}"
echo ""
echo -e "${GREEN}3.${NC} Login from different device and transfer session"
echo -e "   ${CYAN}→ Login on your PC, copy session file to server${NC}"
echo ""
echo -e "${GREEN}4.${NC} Wait 24 hours and try again"
echo -e "   ${CYAN}→ Sometimes Instagram temporarily blocks IPs${NC}"
echo ""
read -p "Select option (1-4): " choice

case $choice in
    1)
        echo ""
        echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}Method 1: Import Session from Browser${NC}"
        echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
        echo ""
        
        source venv/bin/activate
        python3 scripts/login_manual.py
        ;;
        
    2)
        echo ""
        echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}Method 2: Setup Proxy/VPN${NC}"
        echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
        echo ""
        
        echo -e "${YELLOW}To use a proxy, add these to your .env file:${NC}"
        echo ""
        echo -e "${BLUE}# Proxy Settings (optional)${NC}"
        echo -e "${BLUE}PROXY_URL=http://username:password@proxy-server:port${NC}"
        echo -e "${BLUE}# Or for SOCKS5:${NC}"
        echo -e "${BLUE}PROXY_URL=socks5://username:password@proxy-server:port${NC}"
        echo ""
        echo -e "${YELLOW}After adding proxy:${NC}"
        echo -e "  1. Save .env file"
        echo -e "  2. Run: ${GREEN}bash scripts/login.sh${NC}"
        echo ""
        ;;
        
    3)
        echo ""
        echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}Method 3: Transfer Session from Another Device${NC}"
        echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
        echo ""
        
        echo -e "${YELLOW}Steps:${NC}"
        echo ""
        echo -e "${BLUE}On your PC/Laptop (where Instagram doesn't block):${NC}"
        echo "  1. Install: pip install instagrapi"
        echo "  2. Create a Python script:"
        echo ""
        echo -e "${GREEN}from instagrapi import Client${NC}"
        echo -e "${GREEN}cl = Client()${NC}"
        echo -e "${GREEN}cl.login('your_username', 'your_password')${NC}"
        echo -e "${GREEN}cl.dump_settings('session.json')${NC}"
        echo ""
        echo "  3. Run the script (enter 2FA code if prompted)"
        echo "  4. Copy session.json to server:"
        echo ""
        echo -e "${BLUE}On your server:${NC}"
        echo "  scp session.json root@your-server:/var/www/miladrajabi.com/instagram-telegram-bot/sessions/"
        echo "  mv sessions/session.json sessions/\${INSTAGRAM_USERNAME}_session.json"
        echo ""
        ;;
        
    4)
        echo ""
        echo -e "${YELLOW}Waiting is sometimes the best solution.${NC}"
        echo -e "${YELLOW}Use Instagram app normally on your phone for 24 hours.${NC}"
        echo -e "${YELLOW}Then try: bash scripts/login.sh${NC}"
        echo ""
        ;;
        
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
