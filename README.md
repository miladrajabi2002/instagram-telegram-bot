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
- 2FA/Challenge handling

✅ **Telegram Control:**
- Start/stop automation tasks
- View real-time statistics
- Check logs remotely
- Adjust rate limits

✅ **Easy Setup:**
- Interactive setup wizard
- Standalone login script with 2FA support
- One-command installation

---

## Quick Start (3 Commands)

### Prerequisites

Only these need to be installed on your server:
- Python 3.8+ 
- MySQL 5.7+
- Git

```bash
# Install prerequisites (Ubuntu/Debian)
sudo apt update
sudo apt install -y python3 python3-venv python3-pip mysql-server git
```

### Installation

```bash
# 1. Clone repository
git clone https://github.com/miladrajabi2002/instagram-telegram-bot.git
cd instagram-telegram-bot

# 2. Run interactive setup (will ask for all credentials)
bash setup.sh

# 3. Login to Instagram (supports 2FA)
bash scripts/login.sh

# 4. Start the bot
bash scripts/run.sh
```

That's it! 🎉

---

## Detailed Setup Guide

### Step 1: Setup MySQL Database

Before running setup, create the database:

```bash
sudo mysql -u root -p
```

Run these SQL commands:

```sql
CREATE DATABASE instagram_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'instagram_bot_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON instagram_bot.* TO 'instagram_bot_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Import the schema:

```bash
mysql -u root -p instagram_bot < sql/schema.sql
```

### Step 2: Get Telegram Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Copy the token (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 3: Get Your Telegram User ID

1. Open Telegram and search for **@userinfobot**
2. Send `/start` command
3. Copy your user ID (a number like: `123456789`)

### Step 4: Run Setup Wizard

```bash
bash setup.sh
```

The wizard will ask for:
- ✅ Telegram Bot Token
- ✅ Your Telegram User ID
- ✅ Instagram Username
- ✅ Instagram Password
- ✅ MySQL credentials

It will:
- ✅ Create Python virtual environment
- ✅ Install all dependencies
- ✅ Generate encryption key
- ✅ Create `.env` configuration file
- ✅ Test database connection

### Step 5: Login to Instagram

```bash
bash scripts/login.sh
```

**If you have 2FA enabled (Two-Factor Authentication):**
- The script will detect it automatically
- You'll be prompted to enter your 6-digit code
- The session will be saved after successful verification
- You won't need to login again unless session expires

**Output when successful:**
```
🔐 Logging in to Instagram...

Username: your_username

✅ Login successful!
✅ Session saved to: sessions/your_username_session.json
✅ Your Instagram User ID: 123456789
```

### Step 6: Start the Bot

```bash
bash scripts/run.sh
```

The bot will start and you'll see:
```
Instagram Telegram Bot Starting
==================================================
Bot initialized successfully
Starting bot polling...
```

**To stop:** Press `Ctrl+C`

---

## Running as Service (Production)

For permanent background operation:

```bash
# Install systemd service
sudo cp systemd/instagram-bot.service /etc/systemd/system/

# Edit paths if needed
sudo nano /etc/systemd/system/instagram-bot.service

# Reload systemd
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

After starting the bot, open Telegram and message your bot:

### Getting Started

- `/start` - Initialize bot
- `/help` - Show all commands
- `/login` - Login to Instagram (if not already logged in)
- `/status` - Check bot status

### Task Management

- `/start_tasks` - Show menu to start automation modules
- `/stop_tasks` - Stop all running tasks
- `/pause` - Pause task execution
- `/resume` - Resume paused tasks

### Monitoring

- `/stats` - View detailed statistics (7 days)
- `/limits` - Show current rate limits
- `/logs` - View recent log entries

---

## Troubleshooting

### Setup Issues

**Python not found:**
```bash
sudo apt install python3 python3-venv python3-pip
```

**MySQL connection failed:**
```bash
# Check MySQL is running
sudo systemctl status mysql

# Verify credentials
mysql -u instagram_bot_user -p instagram_bot
```

**Permission denied:**
```bash
chmod +x setup.sh scripts/*.sh
```

### Login Issues

**2FA code invalid:**
- Make sure you're entering the current 6-digit code
- Code expires after ~30 seconds, request a new one if needed
- Try again: `bash scripts/login.sh`

**Challenge required:**
```
1. Open Instagram app on your phone
2. You may see a security check - complete it
3. Wait 5-10 minutes
4. Try login again: bash scripts/login.sh
```

**Session expired:**
```bash
# Delete old session
rm -rf sessions/*

# Login again
bash scripts/login.sh
```

### Runtime Issues

**Bot crashes immediately:**
```bash
# Check configuration
cat .env

# Check logs
tail -f logs/bot.log

# Test configuration
source venv/bin/activate
python -c "import config; print('Config OK')"
```

**Rate limiting / Action blocked:**

Edit `.env` and reduce limits:
```ini
MAX_FOLLOWS_PER_DAY=15
MAX_FOLLOWS_PER_HOUR=3
MIN_ACTION_DELAY=120
MAX_ACTION_DELAY=900
```

Then restart:
```bash
bash scripts/run.sh
# or
sudo systemctl restart instagram-bot
```

**Database errors:**
```bash
# Verify tables exist
mysql -u instagram_bot_user -p instagram_bot -e "SHOW TABLES;"

# Reimport schema if needed
mysql -u instagram_bot_user -p instagram_bot < sql/schema.sql
```

### View Logs

```bash
# Real-time logs
tail -f logs/bot.log

# Last 100 lines
tail -n 100 logs/bot.log

# Search for errors
grep -i error logs/bot.log

# Systemd logs (if using service)
sudo journalctl -u instagram-bot -n 100 --no-pager
```

---

## Safety Guidelines

### Recommended Limits by Account Age

**New accounts (<3 months):**
```ini
MAX_FOLLOWS_PER_DAY=15
MAX_LIKES_PER_DAY=50
MAX_COMMENTS_PER_DAY=10
```

**Established accounts (3-12 months):**
```ini
MAX_FOLLOWS_PER_DAY=30
MAX_LIKES_PER_DAY=100
MAX_COMMENTS_PER_DAY=20
```

**Aged accounts (>1 year):**
```ini
MAX_FOLLOWS_PER_DAY=50
MAX_LIKES_PER_DAY=150
MAX_COMMENTS_PER_DAY=30
```

### Best Practices

1. **Start slow:** Use minimal limits for first 1-2 weeks
2. **Increase gradually:** Add 10-20% per week if no issues
3. **Use during active hours:** Run automation when you'd normally use Instagram
4. **Mix manual activity:** Use Instagram manually alongside automation
5. **Monitor closely:** Check `/stats` and logs daily
6. **Respect blocks:** If action blocked, reduce limits by 50% immediately

### Warning Signs - Stop If You See:

⚠️ Action blocked repeatedly
⚠️ "Try again later" errors
⚠️ Login challenges frequently
⚠️ Sudden follower drops

---

## File Structure

```
instagram-telegram-bot/
├── setup.sh                 # Interactive setup wizard
├── scripts/
│   ├── login.sh            # Standalone login (2FA support)
│   ├── run.sh              # Start bot
│   └── generate_key.py     # Generate encryption key
├── bot/                    # Telegram interface
│   └── telegram_bot.py
├── core/                   # Instagram automation core
│   ├── insta_client.py     # API wrapper
│   └── scheduler.py        # Task scheduling
├── modules/                # Automation strategies
│   ├── follow_followers_of_followers.py
│   ├── like_stories_of_followers.py
│   ├── comment_emoji.py
│   └── unfollow_after_delay.py
├── includes/               # Utilities
│   ├── database.py
│   ├── security.py
│   └── logger.py
├── sql/
│   └── schema.sql          # Database schema
├── systemd/
│   └── instagram-bot.service
├── main.py                 # Entry point
├── config.py               # Configuration
├── requirements.txt
└── .env                    # Your credentials (created by setup)
```

---

## FAQ

**Q: Do I need to keep my computer/server on?**
A: Yes, for the bot to work continuously. Use systemd service for auto-restart.

**Q: Will this get my account banned?**
A: If you follow the safety guidelines and use conservative limits, risk is minimal. Start slow.

**Q: Can I run multiple Instagram accounts?**
A: No, this bot is designed for single-account use only.

**Q: Do I need a Telegram account?**
A: Yes, Telegram is the control interface for the bot.

**Q: How do I update the bot?**
```bash
cd instagram-telegram-bot
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
bash scripts/run.sh
```

**Q: How do I change rate limits?**
Edit `.env` file and restart the bot:
```bash
nano .env
# Edit MAX_FOLLOWS_PER_DAY, etc.
bash scripts/run.sh
```

---

## Support

For issues:
1. Check logs: `tail -f logs/bot.log`
2. Review troubleshooting section above
3. Verify `.env` configuration
4. Check Instagram for security challenges
5. Reduce rate limits if experiencing blocks

---

## License

MIT License - Use at your own risk.

## Disclaimer

⚠️ **Important:**
- For educational and personal use only
- Instagram may restrict or ban accounts using automation
- Use conservative limits and monitor closely
- Developer not responsible for any account restrictions

---

**Made with ❤️ for safe Instagram growth**
