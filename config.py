"""Configuration management for Instagram Telegram Bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent
SESSION_DIR = Path(os.getenv('SESSION_FILE_PATH', BASE_DIR / 'sessions'))
LOG_DIR = Path(os.getenv('LOG_FILE', BASE_DIR / 'logs' / 'bot.log')).parent

# Create directories if they don't exist
SESSION_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_ADMIN_ID = int(os.getenv('TELEGRAM_ADMIN_ID', 0))

# Instagram Configuration
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME', '')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD', '')

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_NAME', 'instagram_bot'),
    'user': os.getenv('DB_USER', 'instagram_bot_user'),
    'password': os.getenv('DB_PASSWORD', ''),
}

# Security
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', '').encode()

# Rate Limits (Conservative for safety)
RATE_LIMITS = {
    'follows_per_day': int(os.getenv('MAX_FOLLOWS_PER_DAY', 30)),
    'follows_per_hour': int(os.getenv('MAX_FOLLOWS_PER_HOUR', 5)),
    'likes_per_day': int(os.getenv('MAX_LIKES_PER_DAY', 100)),
    'likes_per_hour': int(os.getenv('MAX_LIKES_PER_HOUR', 15)),
    'comments_per_day': int(os.getenv('MAX_COMMENTS_PER_DAY', 20)),
    'comments_per_hour': int(os.getenv('MAX_COMMENTS_PER_HOUR', 3)),
    'story_views_per_day': int(os.getenv('MAX_STORY_VIEWS_PER_DAY', 150)),
    'story_views_per_hour': int(os.getenv('MAX_STORY_VIEWS_PER_HOUR', 25)),
    'unfollows_per_day': int(os.getenv('MAX_UNFOLLOWS_PER_DAY', 30)),
}

# Unfollow Settings
UNFOLLOW_AFTER_DAYS = int(os.getenv('UNFOLLOW_AFTER_DAYS', 7))

# Action Intervals (in seconds)
MIN_ACTION_DELAY = int(os.getenv('MIN_ACTION_DELAY', 60))
MAX_ACTION_DELAY = int(os.getenv('MAX_ACTION_DELAY', 600))

# Retry Settings
MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
RETRY_DELAY_BASE = int(os.getenv('RETRY_DELAY_BASE', 60))

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', str(LOG_DIR / 'bot.log'))

# Emoji pool for comments (safe, positive emojis)
EMOJI_COMMENTS = [
    '❤️', '😍', '🔥', '👏', '✨', '💯', '😊', '🙌',
    '👍', '💪', '🎉', '⭐', '💖', '🌟', '👌', '😎'
]

# Validation
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is required in .env file")

if not TELEGRAM_ADMIN_ID:
    raise ValueError("TELEGRAM_ADMIN_ID is required in .env file")

if not ENCRYPTION_KEY:
    from cryptography.fernet import Fernet
    print("WARNING: ENCRYPTION_KEY not set. Generate one with:")
    print(f"  {Fernet.generate_key().decode()}")
    raise ValueError("ENCRYPTION_KEY is required in .env file")
