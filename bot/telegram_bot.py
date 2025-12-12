"""Telegram bot for Instagram automation control."""
import logging
import asyncio
from typing import Optional
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

import config
from core.insta_client import InstagramClient
from core.scheduler import TaskScheduler
from modules import (
    FollowFollowersOfFollowers,
    LikeStoriesOfFollowers,
    CommentEmoji,
    UnfollowAfterDelay
)
from includes.database import Database
from includes.logger import setup_logger

logger = setup_logger(__name__)


class TelegramBot:
    """Telegram bot interface for Instagram automation."""

    def __init__(self):
        """Initialize Telegram bot."""
        self.app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        self.db = Database()
        self.insta_client: Optional[InstagramClient] = None
        self.scheduler: Optional[TaskScheduler] = None
        self.modules = {}
        self.is_running = False
        self.awaiting_2fa = False
        self.current_message_id = None  # For updating messages
        
        # Register handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register command and callback handlers."""
        # Commands
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("login", self.cmd_login))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        
        # Manual actions
        self.app.add_handler(CommandHandler("follow", self.cmd_follow))
        self.app.add_handler(CommandHandler("unfollow", self.cmd_unfollow))
        self.app.add_handler(CommandHandler("like", self.cmd_like))
        
        # Automation
        self.app.add_handler(CommandHandler("start_scheduler", self.cmd_start_scheduler))
        self.app.add_handler(CommandHandler("stop_scheduler", self.cmd_stop_scheduler))
        self.app.add_handler(CommandHandler("pause", self.cmd_pause))
        self.app.add_handler(CommandHandler("resume", self.cmd_resume))
        
        # Info
        self.app.add_handler(CommandHandler("limits", self.cmd_limits))
        self.app.add_handler(CommandHandler("logs", self.cmd_logs))
        self.app.add_handler(CommandHandler("report", self.cmd_report))
        
        # Callback queries
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Message handler for 2FA
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    def _check_admin(self, user_id: int) -> bool:
        """Check if user is admin.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if admin
        """
        return user_id == config.TELEGRAM_ADMIN_ID

    async def send_notification(self, message: str):
        """Send notification to admin.
        
        Args:
            message: Notification message
        """
        try:
            await self.app.bot.send_message(
                chat_id=config.TELEGRAM_ADMIN_ID,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    async def update_message(self, message_id: int, text: str):
        """Update existing message.
        
        Args:
            message_id: Message ID to update
            text: New text
        """
        try:
            await self.app.bot.edit_message_text(
                chat_id=config.TELEGRAM_ADMIN_ID,
                message_id=message_id,
                text=text,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to update message: {e}")

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if not self._check_admin(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        text = (
            "🤖 <b>Instagram Automation Bot</b>\n\n"
            "Welcome! This bot helps you automate Instagram tasks safely.\n\n"
            "Use /help to see available commands."
        )
        await update.message.reply_text(text, parse_mode='HTML')

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not self._check_admin(update.effective_user.id):
            return
        
        text = (
            "<b>📊 Commands:</b>\n\n"
            "<b>Setup:</b>\n"
            "/login - Login to Instagram\n\n"
            "<b>Manual Actions:</b>\n"
            "/follow <username> - Follow a user\n"
            "/unfollow <username> - Unfollow a user\n"
            "/like <post_url> - Like a post\n\n"
            "<b>Automation:</b>\n"
            "/start_scheduler - Start automation\n"
            "/stop_scheduler - Stop automation\n"
            "/pause - Pause tasks\n"
            "/resume - Resume tasks\n\n"
            "<b>Info:</b>\n"
            "/status - Check bot status\n"
            "/stats - View statistics\n"
            "/report - Daily activity report\n"
            "/limits - View rate limits\n"
            "/logs - View recent logs\n"
        )
        await update.message.reply_text(text, parse_mode='HTML')

    async def cmd_login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /login command."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if self.insta_client and self.insta_client.is_logged_in:
            await update.message.reply_text("✅ Already logged in!")
            return
        
        try:
            await update.message.reply_text("🔑 Logging in to Instagram...")
            
            # Create client
            self.insta_client = InstagramClient(
                username=config.INSTAGRAM_USERNAME,
                password=config.INSTAGRAM_PASSWORD,
                telegram_notifier=lambda msg: asyncio.create_task(self.send_notification(msg))
            )
            
            # Create scheduler
            self.scheduler = TaskScheduler(
                telegram_notifier=lambda msg: asyncio.create_task(self.send_notification(msg))
            )
            
            # Attempt login
            success = self.insta_client.login()
            
            if success:
                # Initialize modules
                self.modules = {
                    'follow': FollowFollowersOfFollowers(self.insta_client, self.scheduler),
                    'stories': LikeStoriesOfFollowers(self.insta_client, self.scheduler),
                    'comment': CommentEmoji(self.insta_client, self.scheduler),
                    'unfollow': UnfollowAfterDelay(self.insta_client, self.scheduler)
                }
                
                await update.message.reply_text("✅ Login successful!")
            else:
                self.awaiting_2fa = True
                await update.message.reply_text(
                    "⚠️ 2FA required. Please send your 2FA code."
                )
                
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Login failed: {str(e)}")

    async def cmd_follow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /follow <username> command."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if not self.insta_client or not self.insta_client.is_logged_in:
            await update.message.reply_text("❌ Please login first with /login")
            return
        
        if not context.args:
            await update.message.reply_text("📝 Usage: /follow <username>")
            return
        
        username = context.args[0].replace('@', '')
        
        try:
            # Initial message
            msg = await update.message.reply_text(
                f"🔍 <b>Looking up @{username}...</b>",
                parse_mode='HTML'
            )
            
            # Get user info
            user_info = self.insta_client.client.user_info_by_username(username)
            user_id = user_info.pk
            
            await self.update_message(
                msg.message_id,
                f"👤 <b>Following @{username}</b>\n\n"
                f"⏱️ Preparing to follow...\n"
                f"<i>Waiting for human-like delay ({config.MIN_ACTION_DELAY}-{config.MAX_ACTION_DELAY}s)</i>"
            )
            
            # Follow
            success = self.insta_client.safe_follow(user_id)
            
            if success:
                # Get current stats
                stats = self.insta_client.get_stats()
                
                await self.update_message(
                    msg.message_id,
                    f"✅ <b>Successfully followed @{username}</b>\n\n"
                    f"📊 <b>Today's Activity:</b>\n"
                    f"• Follows: {stats.get('follow', 0)}\n"
                    f"• Likes: {stats.get('like', 0)}\n"
                    f"• Comments: {stats.get('comment', 0)}\n"
                    f"• Story Views: {stats.get('story_view', 0)}"
                )
                
                self.db.add_follow_record(str(user_id), username, "manual")
                self.db.log_action('follow', str(user_id), True, f"Manual follow via Telegram")
            else:
                await self.update_message(
                    msg.message_id,
                    f"❌ <b>Failed to follow @{username}</b>\n\n"
                    f"⚠️ Check logs for details."
                )
                
        except Exception as e:
            logger.error(f"Follow error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_unfollow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unfollow <username> command."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if not self.insta_client or not self.insta_client.is_logged_in:
            await update.message.reply_text("❌ Please login first with /login")
            return
        
        if not context.args:
            await update.message.reply_text("📝 Usage: /unfollow <username>")
            return
        
        username = context.args[0].replace('@', '')
        
        try:
            msg = await update.message.reply_text(
                f"🔍 <b>Looking up @{username}...</b>",
                parse_mode='HTML'
            )
            
            # Get user info
            user_info = self.insta_client.client.user_info_by_username(username)
            user_id = user_info.pk
            
            await self.update_message(
                msg.message_id,
                f"👤 <b>Unfollowing @{username}</b>\n\n"
                f"⏱️ Preparing to unfollow...\n"
                f"<i>Waiting for human-like delay</i>"
            )
            
            # Unfollow
            success = self.insta_client.safe_unfollow(user_id)
            
            if success:
                await self.update_message(
                    msg.message_id,
                    f"✅ <b>Successfully unfollowed @{username}</b>"
                )
                
                self.db.add_unfollow_record(str(user_id))
                self.db.log_action('unfollow', str(user_id), True, f"Manual unfollow via Telegram")
            else:
                await self.update_message(
                    msg.message_id,
                    f"❌ <b>Failed to unfollow @{username}</b>"
                )
                
        except Exception as e:
            logger.error(f"Unfollow error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_like(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /like <post_url> command."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if not self.insta_client or not self.insta_client.is_logged_in:
            await update.message.reply_text("❌ Please login first with /login")
            return
        
        if not context.args:
            await update.message.reply_text("📝 Usage: /like <post_url>")
            return
        
        post_url = context.args[0]
        
        try:
            msg = await update.message.reply_text(
                f"👍 <b>Preparing to like post...</b>",
                parse_mode='HTML'
            )
            
            # Get media ID from URL
            media_id = self.insta_client.client.media_pk_from_url(post_url)
            
            await self.update_message(
                msg.message_id,
                f"👍 <b>Liking post...</b>\n\n"
                f"⏱️ Waiting for human-like delay..."
            )
            
            # Like
            success = self.insta_client.safe_like(media_id)
            
            if success:
                stats = self.insta_client.get_stats()
                
                await self.update_message(
                    msg.message_id,
                    f"✅ <b>Post liked successfully</b>\n\n"
                    f"📊 <b>Today's Activity:</b>\n"
                    f"• Likes: {stats.get('like', 0)}\n"
                    f"• Follows: {stats.get('follow', 0)}"
                )
                
                self.db.log_action('like', str(media_id), True, f"Manual like via Telegram")
            else:
                await self.update_message(
                    msg.message_id,
                    f"❌ <b>Failed to like post</b>"
                )
                
        except Exception as e:
            logger.error(f"Like error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        if not self._check_admin(update.effective_user.id):
            return
        
        # Instagram status
        insta_status = "✅ Logged in" if (self.insta_client and self.insta_client.is_logged_in) else "❌ Not logged in"
        
        # Scheduler status
        scheduler_status = "❌ Not started"
        if self.scheduler:
            if self.scheduler.is_paused():
                scheduler_status = "⏸️ Paused"
            elif self.scheduler.running:
                scheduler_status = "▶️ Running"
            else:
                scheduler_status = "⏹️ Stopped"
        
        stats = self.scheduler.get_stats() if self.scheduler else {}
        
        text = (
            f"<b>📊 Bot Status</b>\n\n"
            f"<b>Instagram:</b> {insta_status}\n"
            f"<b>Scheduler:</b> {scheduler_status}\n"
            f"<b>Queue:</b> {stats.get('queue_size', 0)} tasks\n"
            f"<b>Completed:</b> {stats.get('tasks_completed', 0)}\n"
            f"<b>Failed:</b> {stats.get('tasks_failed', 0)}\n"
        )
        
        await update.message.reply_text(text, parse_mode='HTML')

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command."""
        if not self._check_admin(update.effective_user.id):
            return
        
        try:
            # Get statistics from database
            db_stats = self.db.get_statistics(days=7)
            
            # Get action counts from client
            client_stats = self.insta_client.get_stats() if self.insta_client else {}
            
            text = (
                "<b>📈 Statistics (Last 7 Days)</b>\n\n"
                f"<b>Follows:</b> {db_stats.get('follow_count', 0)}\n"
                f"<b>Unfollows:</b> {db_stats.get('unfollows', 0)}\n"
                f"<b>Likes:</b> {db_stats.get('like_count', 0)}\n"
                f"<b>Comments:</b> {db_stats.get('comment_count', 0)}\n"
                f"<b>Story Views:</b> {db_stats.get('story_view_count', 0)}\n"
                f"<b>Active Follows:</b> {db_stats.get('active_follows', 0)}\n\n"
                "<b>Current Session:</b>\n"
                f"Follows: {client_stats.get('follow', 0)}\n"
                f"Likes: {client_stats.get('like', 0)}\n"
                f"Comments: {client_stats.get('comment', 0)}\n"
                f"Story Views: {client_stats.get('story_view', 0)}\n"
            )
            
            await update.message.reply_text(text, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Stats error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /report command - Daily activity report."""
        if not self._check_admin(update.effective_user.id):
            return
        
        try:
            # Get today's statistics
            db_stats = self.db.get_statistics(days=1)
            client_stats = self.insta_client.get_stats() if self.insta_client else {}
            
            # Calculate percentages of daily limits
            follows_pct = (db_stats.get('follow_count', 0) / config.RATE_LIMITS['follows_per_day']) * 100
            likes_pct = (db_stats.get('like_count', 0) / config.RATE_LIMITS['likes_per_day']) * 100
            
            text = (
                f"<b>📅 Daily Activity Report</b>\n"
                f"<i>{datetime.now().strftime('%Y-%m-%d')}</i>\n\n"
                
                f"<b>👥 Follows:</b> {db_stats.get('follow_count', 0)}/{config.RATE_LIMITS['follows_per_day']} "
                f"({follows_pct:.0f}%)\n"
                
                f"<b>👍 Likes:</b> {db_stats.get('like_count', 0)}/{config.RATE_LIMITS['likes_per_day']} "
                f"({likes_pct:.0f}%)\n"
                
                f"<b>💬 Comments:</b> {db_stats.get('comment_count', 0)}/{config.RATE_LIMITS['comments_per_day']}\n"
                f"<b>👁️ Story Views:</b> {db_stats.get('story_view_count', 0)}/{config.RATE_LIMITS['story_views_per_day']}\n"
                f"<b>🚫 Unfollows:</b> {db_stats.get('unfollows', 0)}/{config.RATE_LIMITS['unfollows_per_day']}\n\n"
                
                f"<b>⏱️ Action Delay:</b> {config.MIN_ACTION_DELAY}-{config.MAX_ACTION_DELAY}s\n"
                f"<b>🔄 Active Follows:</b> {db_stats.get('active_follows', 0)}"
            )
            
            await update.message.reply_text(text, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Report error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_start_scheduler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start_scheduler command."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if not self.insta_client or not self.insta_client.is_logged_in:
            await update.message.reply_text("❌ Please login first with /login")
            return
        
        if not self.scheduler:
            await update.message.reply_text("❌ Scheduler not initialized")
            return
        
        if self.scheduler.running:
            await update.message.reply_text("⚠️ Scheduler already running")
            return
        
        self.scheduler.start()
        
        # Initialize modules if not done
        if not self.modules:
            self.modules = {
                'follow': FollowFollowersOfFollowers(self.insta_client, self.scheduler),
                'stories': LikeStoriesOfFollowers(self.insta_client, self.scheduler),
                'comment': CommentEmoji(self.insta_client, self.scheduler),
                'unfollow': UnfollowAfterDelay(self.insta_client, self.scheduler)
            }
        
        # Start all modules
        self.modules['follow'].run()
        self.modules['stories'].run()
        self.modules['unfollow'].run()
        
        await update.message.reply_text("✅ Scheduler started! Automation is now running.")

    async def cmd_stop_scheduler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop_scheduler command."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if self.scheduler:
            self.scheduler.stop()
            await update.message.reply_text("⏹️ Scheduler stopped")
        else:
            await update.message.reply_text("❌ Scheduler not initialized")

    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pause command."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if self.scheduler:
            self.scheduler.pause()
            await update.message.reply_text("⏸️ Tasks paused")
        else:
            await update.message.reply_text("❌ Scheduler not initialized")

    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /resume command."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if self.scheduler:
            self.scheduler.resume()
            await update.message.reply_text("▶️ Tasks resumed")
        else:
            await update.message.reply_text("❌ Scheduler not initialized")

    async def cmd_limits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /limits command."""
        if not self._check_admin(update.effective_user.id):
            return
        
        limits = config.RATE_LIMITS
        text = (
            "<b>⚠️ Current Rate Limits</b>\n\n"
            f"<b>Follows:</b> {limits['follows_per_day']}/day, {limits['follows_per_hour']}/hour\n"
            f"<b>Likes:</b> {limits['likes_per_day']}/day, {limits['likes_per_hour']}/hour\n"
            f"<b>Comments:</b> {limits['comments_per_day']}/day, {limits['comments_per_hour']}/hour\n"
            f"<b>Story Views:</b> {limits['story_views_per_day']}/day, {limits['story_views_per_hour']}/hour\n"
            f"<b>Unfollows:</b> {limits['unfollows_per_day']}/day\n\n"
            f"<b>Unfollow After:</b> {config.UNFOLLOW_AFTER_DAYS} days\n\n"
            f"<b>Action Delay:</b> {config.MIN_ACTION_DELAY}-{config.MAX_ACTION_DELAY} seconds\n\n"
            "<i>Edit .env file to change limits</i>"
        )
        
        await update.message.reply_text(text, parse_mode='HTML')

    async def cmd_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /logs command."""
        if not self._check_admin(update.effective_user.id):
            return
        
        try:
            # Read last 50 lines of log file
            with open(config.LOG_FILE, 'r') as f:
                lines = f.readlines()
                last_lines = lines[-50:] if len(lines) > 50 else lines
                log_text = ''.join(last_lines)
            
            # Truncate if too long
            if len(log_text) > 4000:
                log_text = "..." + log_text[-4000:]
            
            await update.message.reply_text(f"<pre>{log_text}</pre>", parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error reading logs: {str(e)}")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()
        
        if not self._check_admin(query.from_user.id):
            return
        
        # Handle callbacks if needed
        pass

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (for 2FA code)."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if self.awaiting_2fa:
            code = update.message.text.strip()
            
            if self.insta_client:
                success = self.insta_client.verify_2fa(code)
                
                if success:
                    self.awaiting_2fa = False
                    await update.message.reply_text("✅ 2FA verification successful!")
                    
                    # Initialize modules
                    self.modules = {
                        'follow': FollowFollowersOfFollowers(self.insta_client, self.scheduler),
                        'stories': LikeStoriesOfFollowers(self.insta_client, self.scheduler),
                        'comment': CommentEmoji(self.insta_client, self.scheduler),
                        'unfollow': UnfollowAfterDelay(self.insta_client, self.scheduler)
                    }
                else:
                    await update.message.reply_text("❌ Invalid code. Please try again.")

    def run(self):
        """Start the bot."""
        logger.info("Starting Telegram bot...")
        self.app.run_polling()
