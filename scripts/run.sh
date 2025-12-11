#!/bin/bash
# Run the Instagram Telegram Bot

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Instagram Telegram Bot${NC}"
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

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo -e "${YELLOW}Run setup first: bash setup.sh${NC}"
    exit 1
fi

# Check if session exists
if [ ! -d "sessions" ] || [ -z "$(ls -A sessions 2>/dev/null)" ]; then
    echo -e "${YELLOW}⚠️  No Instagram session found!${NC}"
    echo -e "${YELLOW}You need to login first.${NC}"
    echo ""
    read -p "Do you want to login now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        bash scripts/login.sh
        if [ $? -ne 0 ]; then
            echo -e "${RED}Login failed. Cannot start bot.${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}Please login first: bash scripts/login.sh${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Session found${NC}"
echo -e "${GREEN}✓ Starting bot...${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Activate virtual environment and run
source venv/bin/activate
python main.py
