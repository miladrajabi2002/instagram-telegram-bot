#!/bin/bash
# Interactive Setup Script for Instagram Telegram Bot
# This script configures the bot without installing system dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Instagram Telegram Bot - Setup Wizard${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Check Python
echo -e "${YELLOW}[1/6] Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed!${NC}"
    echo -e "${YELLOW}Install it with: sudo apt install python3 python3-venv python3-pip${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
echo ""

# Setup virtual environment
echo -e "${YELLOW}[2/6] Setting up Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Install dependencies
echo -e "${YELLOW}Installing Python packages...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}✓ All dependencies installed${NC}"
echo ""

# Generate encryption key
echo -e "${YELLOW}[3/6] Generating encryption key...${NC}"
ENCRYPTION_KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
echo -e "${GREEN}✓ Encryption key generated${NC}"
echo ""

# Interactive configuration
echo -e "${YELLOW}[4/6] Bot Configuration${NC}"
echo -e "${BLUE}Please provide the following information:${NC}"
echo ""

# Telegram Bot Token
while true; do
    read -p "Telegram Bot Token (from @BotFather): " TELEGRAM_BOT_TOKEN
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        echo -e "${RED}Bot token cannot be empty!${NC}"
    else
        break
    fi
done

# Telegram Admin ID
while true; do
    read -p "Your Telegram User ID (from @userinfobot): " TELEGRAM_ADMIN_ID
    if [[ ! "$TELEGRAM_ADMIN_ID" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}Admin ID must be a number!${NC}"
    else
        break
    fi
done

# Instagram Username
while true; do
    read -p "Instagram Username: " INSTAGRAM_USERNAME
    if [ -z "$INSTAGRAM_USERNAME" ]; then
        echo -e "${RED}Username cannot be empty!${NC}"
    else
        break
    fi
done

# Instagram Password
while true; do
    read -sp "Instagram Password: " INSTAGRAM_PASSWORD
    echo ""
    if [ -z "$INSTAGRAM_PASSWORD" ]; then
        echo -e "${RED}Password cannot be empty!${NC}"
    else
        break
    fi
done

# MySQL Configuration
echo ""
echo -e "${BLUE}MySQL Database Configuration:${NC}"
read -p "MySQL Host [localhost]: " DB_HOST
DB_HOST=${DB_HOST:-localhost}

read -p "MySQL Port [3306]: " DB_PORT
DB_PORT=${DB_PORT:-3306}

read -p "Database Name [instagram_bot]: " DB_NAME
DB_NAME=${DB_NAME:-instagram_bot}

read -p "MySQL Username [instagram_bot_user]: " DB_USER
DB_USER=${DB_USER:-instagram_bot_user}

while true; do
    read -sp "MySQL Password: " DB_PASSWORD
    echo ""
    if [ -z "$DB_PASSWORD" ]; then
        echo -e "${RED}Database password cannot be empty!${NC}"
    else
        break
    fi
done

echo ""

# Create .env file
echo -e "${YELLOW}[5/6] Creating configuration file...${NC}"

cat > .env << EOF
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_ADMIN_ID=${TELEGRAM_ADMIN_ID}

# Instagram Account
INSTAGRAM_USERNAME=${INSTAGRAM_USERNAME}
INSTAGRAM_PASSWORD=${INSTAGRAM_PASSWORD}

# MySQL Database
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}

# Security
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# Session Storage
SESSION_FILE_PATH=${SCRIPT_DIR}/sessions/

# Rate Limits (Conservative Defaults)
MAX_FOLLOWS_PER_DAY=30
MAX_FOLLOWS_PER_HOUR=5
MAX_LIKES_PER_DAY=100
MAX_LIKES_PER_HOUR=15
MAX_COMMENTS_PER_DAY=20
MAX_COMMENTS_PER_HOUR=3
MAX_STORY_VIEWS_PER_DAY=150
MAX_STORY_VIEWS_PER_HOUR=25

# Unfollow Settings
UNFOLLOW_AFTER_DAYS=7
MAX_UNFOLLOWS_PER_DAY=30

# Action Intervals (seconds)
MIN_ACTION_DELAY=60
MAX_ACTION_DELAY=600

# Retry Settings
MAX_RETRIES=3
RETRY_DELAY_BASE=60

# Logging
LOG_LEVEL=INFO
LOG_FILE=${SCRIPT_DIR}/logs/bot.log
EOF

chmod 600 .env
echo -e "${GREEN}✓ Configuration file created (.env)${NC}"
echo ""

# Create directories
mkdir -p sessions logs
echo -e "${GREEN}✓ Created sessions and logs directories${NC}"

# Test database connection
echo -e "${YELLOW}[6/6] Testing database connection...${NC}"

python3 << PYEOF
import sys
import mysql.connector
from mysql.connector import Error

try:
    connection = mysql.connector.connect(
        host='${DB_HOST}',
        port=${DB_PORT},
        database='${DB_NAME}',
        user='${DB_USER}',
        password='${DB_PASSWORD}'
    )
    if connection.is_connected():
        print('\033[0;32m✓ Database connection successful\033[0m')
        connection.close()
        sys.exit(0)
except Error as e:
    print(f'\033[0;31m✗ Database connection failed: {e}\033[0m')
    print('\033[1;33m')
    print('Please check:')
    print('1. MySQL service is running: sudo systemctl status mysql')
    print('2. Database exists: mysql -u root -p -e "CREATE DATABASE ${DB_NAME};"')
    print('3. User has permissions:')
    print('   mysql -u root -p -e "CREATE USER \\"${DB_USER}\\"@\\"localhost\\" IDENTIFIED BY \\"${DB_PASSWORD}\\";"')
    print('   mysql -u root -p -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO \\"${DB_USER}\\"@\\"localhost\\";"')
    print('   mysql -u root -p -e "FLUSH PRIVILEGES;"')
    print('4. Import schema: mysql -u root -p ${DB_NAME} < sql/schema.sql')
    print('\033[0m')
    sys.exit(1)
PYEOF

DB_TEST_RESULT=$?

if [ $DB_TEST_RESULT -ne 0 ]; then
    echo ""
    echo -e "${RED}Setup completed with database connection issue.${NC}"
    echo -e "${YELLOW}Fix the database issue and run: bash scripts/login.sh${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo -e "${YELLOW}1. Login to Instagram (with 2FA support):${NC}"
echo -e "   bash scripts/login.sh"
echo ""
echo -e "${YELLOW}2. Start the bot:${NC}"
echo -e "   bash scripts/run.sh"
echo ""
echo -e "${YELLOW}3. Or run directly:${NC}"
echo -e "   source venv/bin/activate && python main.py"
echo ""
echo -e "${BLUE}Configuration saved to: .env${NC}"
echo ""
