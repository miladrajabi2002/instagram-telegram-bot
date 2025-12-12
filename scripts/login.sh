#!/bin/bash
# Instagram Login Wrapper Script

set -e

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found!"
    echo "Run setup first: bash setup.sh"
    exit 1
fi

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found!"
    echo "Run setup first: bash setup.sh"
    exit 1
fi

source venv/bin/activate

# Run Python login script
python3 scripts/login.py
