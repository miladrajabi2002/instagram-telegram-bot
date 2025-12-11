#!/bin/bash
# Setup script for Instagram Telegram Bot on Ubuntu

set -e

echo "======================================"
echo "Instagram Telegram Bot Setup"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo"
    exit 1
fi

# Configuration
PROJECT_DIR="/var/www/miladrajabi.com/python/instagram-telegram-bot"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="/var/www/miladrajabi.com/python/logs"
SESSION_DIR="$PROJECT_DIR/sessions"

echo "[1/8] Installing system dependencies..."
apt-get update
apt-get install -y python3 python3-pip python3-venv mysql-server git

echo ""
echo "[2/8] Creating project directories..."
mkdir -p /var/www/miladrajabi.com/python
mkdir -p $LOG_DIR
mkdir -p $SESSION_DIR

echo ""
echo "[3/8] Cloning repository..."
if [ ! -d "$PROJECT_DIR" ]; then
    cd /var/www/miladrajabi.com/python
    git clone https://github.com/miladrajabi2002/instagram-telegram-bot.git
else
    echo "Repository already exists, pulling latest changes..."
    cd $PROJECT_DIR
    git pull
fi

cd $PROJECT_DIR

echo ""
echo "[4/8] Creating Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv venv
fi

echo ""
echo "[5/8] Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "[6/8] Setting up database..."
read -p "Do you want to create the MySQL database? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating database..."
    mysql -u root -p < sql/schema.sql
    echo "Database created successfully!"
    echo ""
    echo "IMPORTANT: Create a MySQL user for the bot:"
    echo "  CREATE USER 'instagram_bot_user'@'localhost' IDENTIFIED BY 'your_secure_password';"
    echo "  GRANT ALL PRIVILEGES ON instagram_bot.* TO 'instagram_bot_user'@'localhost';"
    echo "  FLUSH PRIVILEGES;"
    echo ""
    read -p "Press enter to continue..."
fi

echo ""
echo "[7/8] Configuring environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env file from .env.example"
    echo ""
    echo "IMPORTANT: Edit .env file with your settings:"
    echo "  nano $PROJECT_DIR/.env"
    echo ""
    echo "Required settings:"
    echo "  - TELEGRAM_BOT_TOKEN (get from @BotFather)"
    echo "  - TELEGRAM_ADMIN_ID (your Telegram user ID)"
    echo "  - INSTAGRAM_USERNAME"
    echo "  - INSTAGRAM_PASSWORD"
    echo "  - DB_PASSWORD"
    echo "  - ENCRYPTION_KEY (generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
    echo ""
    read -p "Press enter to continue..."
else
    echo ".env file already exists"
fi

echo ""
echo "[8/8] Setting up systemd service..."
cp systemd/instagram-bot.service /etc/systemd/system/
chown -R www-data:www-data $PROJECT_DIR
chown -R www-data:www-data $LOG_DIR
chmod 600 $PROJECT_DIR/.env  # Protect credentials

systemctl daemon-reload

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit configuration: nano $PROJECT_DIR/.env"
echo "2. Generate encryption key:"
echo "   python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
echo "3. Start the bot:"
echo "   systemctl start instagram-bot"
echo "4. Enable auto-start:"
echo "   systemctl enable instagram-bot"
echo "5. Check status:"
echo "   systemctl status instagram-bot"
echo "6. View logs:"
echo "   journalctl -u instagram-bot -f"
echo ""
echo "Telegram commands:"
echo "  /start - Start the bot"
echo "  /login - Login to Instagram"
echo "  /start_tasks - Start automation"
echo "  /help - Show all commands"
echo ""
