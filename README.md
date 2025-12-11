# Instagram Telegram Bot

🤖 Single-user Telegram bot for safe Instagram automation with human-like behavior.

## Features

✅ **Safe Instagram Automation:**
- Follow followers of your followers
- View and interact with stories
- Leave emoji comments on posts
- Auto-unfollow after configurable delay

✅ **Safety First:**
- Conservative rate limits (30 follows/day default)
- Randomized human-like delays (60-600 seconds)
- Exponential backoff on errors
- 2FA/Challenge handling via Telegram

✅ **Telegram Control:**
- Start/stop automation tasks
- View real-time statistics
- Check logs remotely
- Adjust rate limits

✅ **Database Tracking:**
- MySQL for session persistence
- Action logging and analytics
- Follow/unfollow tracking

---

## Installation

### Prerequisites

- Ubuntu 20.04+ (or Debian-based Linux)
- Python 3.8+
- MySQL 5.7+
- Telegram Bot Token (from @BotFather)

### Quick Setup (Automated)

```bash
# 1. Clone the repository
cd /var/www/miladrajabi.com/python/
git clone https://github.com/miladrajabi2002/instagram-telegram-bot.git
cd instagram-telegram-bot

# 2. Run setup script (as root)
sudo bash setup.sh
```

### Manual Setup

#### 1. Install Dependencies

```bash
# System packages
sudo apt update
sudo apt install -y python3 python3-pip python3-venv mysql-server git

# Create directories
sudo mkdir -p /var/www/miladrajabi.com/python
sudo mkdir -p /var/www/miladrajabi.com/python/logs
```

#### 2. Clone Repository

```bash
cd /var/www/miladrajabi.com/python/
git clone https://github.com/miladrajabi2002/instagram-telegram-bot.git
cd instagram-telegram-bot
```

#### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Setup MySQL Database

```bash
# Login to MySQL
sudo mysql -u root -p

# Run these SQL commands:
CREATE DATABASE instagram_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'instagram_bot_user'@'localhost' IDENTIFIED BY 'YOUR_SECURE_PASSWORD';
GRANT ALL PRIVILEGES ON instagram_bot.* TO 'instagram_bot_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# Import schema
mysql -u root -p instagram_bot < sql/schema.sql
```

#### 5. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Generate encryption key
python3 scripts/generate_key.py

# Edit configuration
nano .env
```

**Required `.env` settings:**

```ini
# Telegram (REQUIRED)
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz  # From @BotFather
TELEGRAM_ADMIN_ID=123456789  # Your Telegram user ID

# Instagram (REQUIRED)
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password

# Database (REQUIRED)
DB_HOST=localhost
DB_PORT=3306
DB_NAME=instagram_bot
DB_USER=instagram_bot_user
DB_PASSWORD=YOUR_SECURE_PASSWORD

# Security (REQUIRED)
ENCRYPTION_KEY=YOUR_GENERATED_FERNET_KEY

# Paths
SESSION_FILE_PATH=/var/www/miladrajabi.com/python/instagram-telegram-bot/sessions/
LOG_FILE=/var/www/miladrajabi.com/python/logs/bot.log

# Rate Limits (Adjust based on your account age)
MAX_FOLLOWS_PER_DAY=30
MAX_FOLLOWS_PER_HOUR=5
MAX_LIKES_PER_DAY=100
MAX_COMMENTS_PER_DAY=20
UNFOLLOW_AFTER_DAYS=7
```

#### 6. Set Permissions

```bash
sudo chown -R www-data:www-data /var/www/miladrajabi.com/python/instagram-telegram-bot
sudo chown -R www-data:www-data /var/www/miladrajabi.com/python/logs
sudo chmod 600 .env  # Protect credentials
```

---

## Running the Bot

### Method 1: Direct Python (For Testing)

```bash
cd /var/www/miladrajabi.com/python/instagram-telegram-bot
source venv/bin/activate
python main.py
```

**To stop:** Press `Ctrl+C`

### Method 2: Systemd Service (Production)

```bash
# Install service
sudo cp systemd/instagram-bot.service /etc/systemd/system/
sudo systemctl daemon-reload

# Start bot
sudo systemctl start instagram-bot

# Enable auto-start on boot
sudo systemctl enable instagram-bot

# Check status
sudo systemctl status instagram-bot

# View logs
sudo journalctl -u instagram-bot -f

# Stop bot
sudo systemctl stop instagram-bot

# Restart bot
sudo systemctl restart instagram-bot
```

---

## Telegram Commands

Once the bot is running, open Telegram and message your bot:

### Basic Commands

- `/start` - Initialize bot and see welcome message
- `/help` - Show all available commands
- `/login` - Login to Instagram (with 2FA support)
- `/status` - Check bot and scheduler status

### Task Management

- `/start_tasks` - Show task menu to start automation
- `/stop_tasks` - Stop all running tasks
- `/pause` - Pause task execution
- `/resume` - Resume paused tasks

### Monitoring

- `/stats` - View detailed statistics
- `/limits` - Show current rate limits
- `/logs` - View recent log entries

---

## Troubleshooting

### Bot doesn't start

**Check Python path:**
```bash
cd /var/www/miladrajabi.com/python/instagram-telegram-bot
source venv/bin/activate
which python  # Should show venv/bin/python
python --version  # Should be 3.8+
```

**Check dependencies:**
```bash
pip list | grep instagrapi
pip list | grep telegram
```

**Install missing packages:**
```bash
pip install -r requirements.txt
```

### Configuration errors

**Test config file:**
```bash
python -c "import config; print('Config OK')"
```

**Common errors:**
- `TELEGRAM_BOT_TOKEN is required` → Add token to `.env`
- `ENCRYPTION_KEY is required` → Generate with `python3 scripts/generate_key.py`

### Database connection issues

**Test MySQL connection:**
```bash
mysql -u instagram_bot_user -p instagram_bot
```

**Check if tables exist:**
```sql
USE instagram_bot;
SHOW TABLES;
```

**Recreate database:**
```bash
mysql -u root -p instagram_bot < sql/schema.sql
```

### Instagram login fails

**2FA Required:**
- Bot will ask for code via Telegram
- Enter the 6-digit code when prompted

**Challenge Required:**
- Open Instagram app
- Complete security challenge
- Retry `/login` in Telegram

**Session expired:**
- Delete session file: `rm sessions/*_session.json`
- Login again with `/login`

### Rate limiting or blocks

**Reduce limits in `.env`:**
```ini
MAX_FOLLOWS_PER_DAY=15  # Start lower for new accounts
MAX_FOLLOWS_PER_HOUR=3
MIN_ACTION_DELAY=120    # Increase delays
MAX_ACTION_DELAY=900
```

**Wait and retry:**
- If blocked, wait 24-48 hours
- Use Instagram normally (manually) during wait
- Start with minimal automation after unblock

### View detailed logs

```bash
# Real-time logs
tail -f /var/www/miladrajabi.com/python/logs/bot.log

# Search for errors
grep -i error /var/www/miladrajabi.com/python/logs/bot.log

# Last 100 lines
tail -n 100 /var/www/miladrajabi.com/python/logs/bot.log
```

### Service won't start

**Check service status:**
```bash
sudo systemctl status instagram-bot
```

**View service logs:**
```bash
sudo journalctl -u instagram-bot -n 50 --no-pager
```

**Check file permissions:**
```bash
ls -la /var/www/miladrajabi.com/python/instagram-telegram-bot/
ls -la /var/www/miladrajabi.com/python/instagram-telegram-bot/.env
```

**Fix permissions:**
```bash
sudo chown -R www-data:www-data /var/www/miladrajabi.com/python/instagram-telegram-bot
sudo chmod 600 /var/www/miladrajabi.com/python/instagram-telegram-bot/.env
```

---

## Safety Guidelines

### Conservative Limits (Recommended)

**New accounts (<3 months):**
- Follows: 10-20/day
- Likes: 50-80/day
- Comments: 5-10/day

**Established accounts (>6 months):**
- Follows: 30-50/day
- Likes: 100-150/day
- Comments: 15-25/day

**Aged accounts (>1 year):**
- Follows: 50-100/day
- Likes: 150-200/day
- Comments: 20-30/day

### Best Practices

1. **Start slow:** Begin with minimal limits for 1-2 weeks
2. **Increase gradually:** Add 10-20% per week if no issues
3. **Use during active hours:** Schedule tasks during your typical usage time
4. **Mix manual activity:** Use Instagram manually alongside automation
5. **Monitor closely:** Check logs and `/stats` daily for warnings
6. **Respect blocks:** If action blocked, reduce limits by 50%

### Warning Signs

⚠️ **Stop automation if you see:**
- "Action blocked" messages
- "Try again later" errors
- Login challenges frequently
- Sudden follower drops

---

## Project Structure

```
instagram-telegram-bot/
├── bot/                    # Telegram bot interface
│   └── telegram_bot.py     # Command handlers
├── core/                   # Core functionality
│   ├── insta_client.py     # Instagram API wrapper
│   └── scheduler.py        # Task scheduling
├── modules/                # Automation modules
│   ├── follow_followers_of_followers.py
│   ├── like_stories_of_followers.py
│   ├── comment_emoji.py
│   └── unfollow_after_delay.py
├── includes/               # Utilities
│   ├── database.py         # MySQL operations
│   ├── security.py         # Encryption
│   └── logger.py           # Logging setup
├── sql/                    # Database schema
│   └── schema.sql
├── systemd/                # System service
│   └── instagram-bot.service
├── scripts/                # Helper scripts
│   └── generate_key.py
├── main.py                 # Entry point
├── config.py               # Configuration
├── requirements.txt        # Dependencies
└── .env                    # Environment variables
```

---

## Contributing

This is a personal project for single-user automation. Use responsibly and respect Instagram's Terms of Service.

## License

MIT License - Use at your own risk.

## Disclaimer

⚠️ **Important:**
- This bot is for educational and personal use only
- Instagram may restrict or ban accounts using automation
- Use conservative limits and monitor closely
- The developer is not responsible for any account restrictions

---

## Support

For issues or questions:
1. Check logs: `/logs` command or `tail -f /var/www/miladrajabi.com/python/logs/bot.log`
2. Review this README's troubleshooting section
3. Check Instagram for any security challenges
4. Reduce rate limits if experiencing blocks

---

**Made with ❤️ for safe Instagram growth**
