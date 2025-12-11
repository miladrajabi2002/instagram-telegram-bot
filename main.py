#!/usr/bin/env python3
"""Main entry point for Instagram Telegram Bot."""
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from bot.telegram_bot import TelegramBot
from includes.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Main function."""
    try:
        logger.info("="*50)
        logger.info("Instagram Telegram Bot Starting")
        logger.info("="*50)
        logger.info(f"Log level: {config.LOG_LEVEL}")
        logger.info(f"Session directory: {config.SESSION_DIR}")
        logger.info(f"Log file: {config.LOG_FILE}")
        
        # Verify configuration
        if not config.TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not configured")
            sys.exit(1)
        
        if not config.TELEGRAM_ADMIN_ID:
            logger.error("TELEGRAM_ADMIN_ID not configured")
            sys.exit(1)
        
        if not config.ENCRYPTION_KEY:
            logger.error("ENCRYPTION_KEY not configured")
            logger.info("Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
            sys.exit(1)
        
        # Create and run bot
        bot = TelegramBot()
        logger.info("Bot initialized successfully")
        logger.info(f"Admin ID: {config.TELEGRAM_ADMIN_ID}")
        logger.info("Starting bot polling...")
        
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
