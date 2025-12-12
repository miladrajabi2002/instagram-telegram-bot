#!/bin/bash
# Complete Instagram Telegram Bot Manager
# This script handles everything: checks, fixes, run, and service management

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║        Instagram Telegram Bot - Complete Manager          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to check requirements
check_requirements() {
    echo -e "${YELLOW}[1/7] Checking requirements...${NC}"
    
    # Check .env
    if [ ! -f ".env" ]; then
        echo -e "${RED}✗ .env file not found${NC}"
        echo -e "${YELLOW}Run: bash setup.sh${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ .env file exists${NC}"
    
    # Check venv
    if [ ! -d "venv" ]; then
        echo -e "${RED}✗ Virtual environment not found${NC}"
        echo -e "${YELLOW}Run: bash setup.sh${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
    
    # Check directories
    mkdir -p sessions logs
    echo -e "${GREEN}✓ Directories created${NC}"
    
    return 0
}

# Function to check session
check_session() {
    echo -e "\n${YELLOW}[2/7] Checking Instagram session...${NC}"
    
    if [ ! -d "sessions" ] || [ -z "$(ls -A sessions 2>/dev/null)" ]; then
        echo -e "${RED}✗ No Instagram session found${NC}"
        echo ""
        read -p "Do you want to login now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            source venv/bin/activate
            python3 scripts/login.py
            if [ $? -ne 0 ]; then
                echo -e "${RED}✗ Login failed${NC}"
                return 1
            fi
        else
            echo -e "${YELLOW}Please login first: python3 scripts/login.py${NC}"
            return 1
        fi
    else
        echo -e "${GREEN}✓ Instagram session found${NC}"
    fi
    
    return 0
}

# Function to check database
check_database() {
    echo -e "\n${YELLOW}[3/7] Checking MySQL database...${NC}"
    
    source venv/bin/activate
    
    python3 << 'PYEOF'
import sys
import mysql.connector
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import config

try:
    conn = mysql.connector.connect(
        host=config.DB_CONFIG['host'],
        port=config.DB_CONFIG['port'],
        database=config.DB_CONFIG['database'],
        user=config.DB_CONFIG['user'],
        password=config.DB_CONFIG['password']
    )
    conn.close()
    print("✓ Database connection OK")
    sys.exit(0)
except Exception as e:
    print(f"✗ Database connection failed: {e}")
    sys.exit(1)
PYEOF
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Database connected${NC}"
        return 0
    else
        echo -e "${RED}✗ Database connection failed${NC}"
        echo -e "${YELLOW}Check your database settings in .env${NC}"
        return 1
    fi
}

# Function to check Telegram bot
check_telegram() {
    echo -e "\n${YELLOW}[4/7] Checking Telegram bot configuration...${NC}"
    
    source venv/bin/activate
    
    python3 << 'PYEOF'
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import config

if not config.TELEGRAM_BOT_TOKEN:
    print("✗ TELEGRAM_BOT_TOKEN not set")
    sys.exit(1)

if not config.TELEGRAM_ADMIN_ID:
    print("✗ TELEGRAM_ADMIN_ID not set")
    sys.exit(1)

print("✓ Telegram configuration OK")
print(f"  Bot Token: {config.TELEGRAM_BOT_TOKEN[:10]}...")
print(f"  Admin ID: {config.TELEGRAM_ADMIN_ID}")
sys.exit(0)
PYEOF
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Telegram bot configured${NC}"
        return 0
    else
        echo -e "${RED}✗ Telegram bot not configured${NC}"
        return 1
    fi
}

# Function to show status
show_status() {
    echo -e "\n${YELLOW}[5/7] Checking bot status...${NC}"
    
    # Check if running via systemd
    if systemctl is-active --quiet instagram-bot 2>/dev/null; then
        echo -e "${GREEN}✓ Bot is running (systemd service)${NC}"
        echo -e "${CYAN}  Status: systemctl status instagram-bot${NC}"
        echo -e "${CYAN}  Logs: journalctl -u instagram-bot -f${NC}"
        return 0
    fi
    
    # Check if running as process
    if pgrep -f "python.*main.py" > /dev/null; then
        echo -e "${GREEN}✓ Bot is running (manual process)${NC}"
        PID=$(pgrep -f "python.*main.py")
        echo -e "${CYAN}  PID: $PID${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}⚠ Bot is not running${NC}"
    return 1
}

# Function to show menu
show_menu() {
    echo -e "\n${YELLOW}[6/7] Choose how to run the bot:${NC}"
    echo ""
    echo -e "${GREEN}1.${NC} Run now (foreground - shows logs, Ctrl+C to stop)"
    echo -e "${GREEN}2.${NC} Run as systemd service (background, auto-restart)"
    echo -e "${GREEN}3.${NC} Stop systemd service"
    echo -e "${GREEN}4.${NC} View logs (systemd service)"
    echo -e "${GREEN}5.${NC} View logs (file)"
    echo -e "${GREEN}6.${NC} Check status only"
    echo -e "${GREEN}7.${NC} Exit"
    echo ""
    read -p "Choose option (1-7): " choice
    
    case $choice in
        1)
            run_foreground
            ;;
        2)
            setup_systemd
            ;;
        3)
            stop_systemd
            ;;
        4)
            view_systemd_logs
            ;;
        5)
            view_file_logs
            ;;
        6)
            show_status
            echo -e "\n${GREEN}Status check complete${NC}\n"
            ;;
        7)
            echo -e "\n${CYAN}Goodbye!${NC}\n"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            show_menu
            ;;
    esac
}

# Function to run in foreground
run_foreground() {
    echo -e "\n${YELLOW}[7/7] Starting bot in foreground...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}\n"
    
    source venv/bin/activate
    python main.py
}

# Function to setup systemd
setup_systemd() {
    echo -e "\n${YELLOW}[7/7] Setting up systemd service...${NC}"
    
    # Update service file with current path
    CURRENT_PATH=$(pwd)
    
    cat > /tmp/instagram-bot.service << EOF
[Unit]
Description=Instagram Telegram Bot
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$CURRENT_PATH
Environment="PATH=$CURRENT_PATH/venv/bin"
ExecStart=$CURRENT_PATH/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=append:$CURRENT_PATH/logs/bot.log
StandardError=append:$CURRENT_PATH/logs/bot-error.log

[Install]
WantedBy=multi-user.target
EOF
    
    # Install service
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}Installing service (requires sudo)...${NC}"
        sudo cp /tmp/instagram-bot.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable instagram-bot
        sudo systemctl start instagram-bot
    else
        cp /tmp/instagram-bot.service /etc/systemd/system/
        systemctl daemon-reload
        systemctl enable instagram-bot
        systemctl start instagram-bot
    fi
    
    rm /tmp/instagram-bot.service
    
    echo -e "${GREEN}✓ Service installed and started${NC}"
    echo ""
    echo -e "${CYAN}Useful commands:${NC}"
    echo -e "  Status: ${YELLOW}sudo systemctl status instagram-bot${NC}"
    echo -e "  Stop: ${YELLOW}sudo systemctl stop instagram-bot${NC}"
    echo -e "  Restart: ${YELLOW}sudo systemctl restart instagram-bot${NC}"
    echo -e "  Logs: ${YELLOW}sudo journalctl -u instagram-bot -f${NC}"
    echo ""
}

# Function to stop systemd
stop_systemd() {
    echo -e "\n${YELLOW}Stopping systemd service...${NC}"
    
    if [ "$EUID" -ne 0 ]; then
        sudo systemctl stop instagram-bot
    else
        systemctl stop instagram-bot
    fi
    
    echo -e "${GREEN}✓ Service stopped${NC}\n"
}

# Function to view systemd logs
view_systemd_logs() {
    echo -e "\n${YELLOW}Viewing systemd logs (Ctrl+C to exit)...${NC}\n"
    
    if [ "$EUID" -ne 0 ]; then
        sudo journalctl -u instagram-bot -n 50 -f
    else
        journalctl -u instagram-bot -n 50 -f
    fi
}

# Function to view file logs
view_file_logs() {
    echo -e "\n${YELLOW}Viewing bot logs (Ctrl+C to exit)...${NC}\n"
    
    if [ -f "logs/bot.log" ]; then
        tail -f logs/bot.log
    else
        echo -e "${RED}No log file found${NC}"
        echo -e "${YELLOW}Run the bot first to generate logs${NC}\n"
    fi
}

# Main execution
echo -e "${CYAN}Starting comprehensive checks...${NC}\n"

# Run all checks
if ! check_requirements; then
    echo -e "\n${RED}✗ Requirements check failed${NC}\n"
    exit 1
fi

if ! check_session; then
    echo -e "\n${RED}✗ Session check failed${NC}\n"
    exit 1
fi

if ! check_database; then
    echo -e "\n${YELLOW}⚠ Database check failed (not critical)${NC}"
    echo -e "${YELLOW}Bot will work but stats/tracking won't be saved${NC}"
fi

if ! check_telegram; then
    echo -e "\n${RED}✗ Telegram configuration failed${NC}\n"
    exit 1
fi

show_status

# Show menu
show_menu
