"""Telegram bot for Instagram automation control."""
import logging
import asyncio
import json
from typing import Optional
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
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
        self.awaiting_json_import = False  # For JSON import
        self.json_import_state = {}  # Store import state
        self.current_message_id = None
        
        # Register handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register command and callback handlers."""
        # Commands
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("menu", self.cmd_menu))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("login", self.cmd_login))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("report", self.cmd_report))
        
        # Manual actions
        self.app.add_handler(CommandHandler("follow", self.cmd_follow))
        self.app.add_handler(CommandHandler("unfollow", self.cmd_unfollow))
        self.app.add_handler(CommandHandler("like", self.cmd_like))
        
        # Automation
        self.app.add_handler(CommandHandler("start_scheduler", self.cmd_start_scheduler))
        self.app.add_handler(CommandHandler("stop_scheduler", self.cmd_stop_scheduler))
        self.app.add_handler(CommandHandler("pause", self.cmd_pause))
        self.app.add_handler(CommandHandler("resume", self.cmd_resume))
        
        # Manual import
        self.app.add_handler(CommandHandler("import_followers", self.cmd_import_followers))
        
        # Info
        self.app.add_handler(CommandHandler("limits", self.cmd_limits))
        self.app.add_handler(CommandHandler("logs", self.cmd_logs))
        
        # Callback queries
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Document handler for JSON import
        self.app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        
        # Text message handler (2FA + unknown)
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Unknown command
        self.app.add_handler(MessageHandler(filters.COMMAND, self.handle_unknown_command))

    def _check_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id == config.TELEGRAM_ADMIN_ID

    async def send_notification(self, message: str):
        """Send notification to admin."""
        try:
            await self.app.bot.send_message(
                chat_id=config.TELEGRAM_ADMIN_ID,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    async def update_message(self, message_id: int, text: str):
        """Update existing message."""
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
            "📚 Use /menu for main menu or /help for commands."
        )
        await update.message.reply_text(text, parse_mode='HTML')

    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command - Show main menu."""
        if not self._check_admin(update.effective_user.id):
            return
        
        keyboard = [
            [InlineKeyboardButton("🔑 Login to Instagram", callback_data="menu_login")],
            [InlineKeyboardButton("📊 Status & Stats", callback_data="menu_stats")],
            [InlineKeyboardButton("⚙️ Automation", callback_data="menu_automation")],
            [InlineKeyboardButton("👤 Manual Actions", callback_data="menu_manual")],
            [InlineKeyboardButton("📎 Manual Import", callback_data="menu_import")],
            [InlineKeyboardButton("ℹ️ Info & Settings", callback_data="menu_info")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "🏠 <b>Main Menu</b>\n\n"
            "Select an option:"
        )
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not self._check_admin(update.effective_user.id):
            return
        
        text = (
            "<b>📚 Complete Command Guide</b>\n\n"
            
            "<b>🔑 Setup</b>\n"
            "/menu - Main menu (recommended!)\n"
            "/login - Login to Instagram\n"
            "/status - Check bot status\n\n"
            
            "<b>👤 Manual Actions</b>\n"
            "/follow &lt;username&gt; - Follow user\n"
            "/unfollow &lt;username&gt; - Unfollow user\n"
            "/like &lt;post_url&gt; - Like post\n\n"
            
            "<b>⚙️ Automation</b>\n"
            "/start_scheduler - Start tasks\n"
            "/stop_scheduler - Stop tasks\n"
            "/pause - Pause tasks\n"
            "/resume - Resume tasks\n\n"
            
            "<b>📎 Manual Import</b>\n"
            "/import_followers - Import followers from JSON\n"
            "<i>Get Instagram GraphQL URL and paste JSON response</i>\n\n"
            
            "<b>📊 Statistics</b>\n"
            "/stats - 7-day statistics\n"
            "/report - Daily report\n"
            "/limits - Rate limits\n"
            "/logs - Recent logs\n\n"
            
            "🆘 Use /menu for easy access!"
        )
        await update.message.reply_text(text, parse_mode='HTML')

    async def handle_unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown commands."""
        if not self._check_admin(update.effective_user.id):
            return
        
        text = (
            "❌ <b>Unknown command!</b>\n\n"
            "📚 Use /menu for main menu or /help for all commands."
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
            
            self.insta_client = InstagramClient(
                username=config.INSTAGRAM_USERNAME,
                password=config.INSTAGRAM_PASSWORD,
                telegram_notifier=lambda msg: asyncio.create_task(self.send_notification(msg))
            )
            
            self.scheduler = TaskScheduler(
                telegram_notifier=lambda msg: asyncio.create_task(self.send_notification(msg))
            )
            
            success = self.insta_client.login()
            
            if success:
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

    async def cmd_import_followers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /import_followers command."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if not self.insta_client:
            await update.message.reply_text("❌ Please /login first")
            return
        
        user_id = self.insta_client.get_my_user_id()
        if not user_id:
            await update.message.reply_text("❌ Failed to get user ID")
            return
        
        # Generate GraphQL URL
        url = (
            f"https://www.instagram.com/graphql/query/"
            f"?variables=%7B%22id%22%3A%22{user_id}%22%2C%22include_reel%22%3Atrue%2C"
            f"%22fetch_mutual%22%3Afalse%2C%22first%22%3A50%7D"
            f"&query_hash=37479f2b8209594dde7facb0d904896a"
        )
        
        self.awaiting_json_import = True
        self.json_import_state = {
            'user_id': user_id,
            'total_imported': 0,
            'pages': 0
        }
        
        text = (
            "📎 <b>Manual Follower Import</b>\n\n"
            "<b>Step 1:</b> Open this URL in your browser (logged in to Instagram):\n"
            f"<code>{url}</code>\n\n"
            "<b>Step 2:</b> Copy the entire JSON response\n\n"
            "<b>Step 3:</b> Save it as a .json or .txt file and send it here\n\n"
            "<b>Or:</b> Just paste the JSON text directly\n\n"
            "<i>For pagination, look for 'end_cursor' in the response and add:</i>\n"
            f"<code>&variables={{...%2C%22after%22%3A%22CURSOR_HERE%22}}</code>"
        )
        
        await update.message.reply_text(text, parse_mode='HTML')

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads (JSON files)."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if not self.awaiting_json_import:
            return
        
        try:
            document = update.message.document
            
            # Download file
            file = await context.bot.get_file(document.file_id)
            file_bytes = await file.download_as_bytearray()
            file_content = file_bytes.decode('utf-8')
            
            # Parse and import
            await self._import_followers_json(update, file_content)
            
        except Exception as e:
            logger.error(f"Document handling error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def _import_followers_json(self, update: Update, json_content: str):
        """Import followers from JSON content."""
        try:
            data = json.loads(json_content)
            
            # Parse Instagram GraphQL response
            user_data = data.get('data', {}).get('user', {})
            edge_followed_by = user_data.get('edge_followed_by', {})
            edges = edge_followed_by.get('edges', [])
            page_info = edge_followed_by.get('page_info', {})
            
            if not edges:
                await update.message.reply_text("⚠️ No followers found in JSON")
                return
            
            # Import followers
            imported = 0
            for edge in edges:
                node = edge.get('node', {})
                user_id = node.get('id')
                username = node.get('username')
                
                if user_id and username:
                    self.db.add_follow_record(user_id, username, "manual_import")
                    imported += 1
            
            self.json_import_state['total_imported'] += imported
            self.json_import_state['pages'] += 1
            
            # Check if more pages
            has_next = page_info.get('has_next_page', False)
            end_cursor = page_info.get('end_cursor', '')
            
            response_text = (
                f"✅ <b>Imported {imported} followers!</b>\n\n"
                f"📊 <b>Total:</b> {self.json_import_state['total_imported']} followers\n"
                f"📄 <b>Pages:</b> {self.json_import_state['pages']}\n\n"
            )
            
            if has_next and end_cursor:
                user_id = self.json_import_state.get('user_id')
                next_url = (
                    f"https://www.instagram.com/graphql/query/"
                    f"?variables=%7B%22id%22%3A%22{user_id}%22%2C%22include_reel%22%3Atrue%2C"
                    f"%22fetch_mutual%22%3Afalse%2C%22first%22%3A50%2C"
                    f"%22after%22%3A%22{end_cursor}%22%7D"
                    f"&query_hash=37479f2b8209594dde7facb0d904896a"
                )
                
                response_text += (
                    "🔄 <b>More pages available!</b>\n\n"
                    "Send next page JSON or click button:\n"
                )
                
                keyboard = [
                    [InlineKeyboardButton("📎 Get Next Page URL", callback_data="get_next_page")],
                    [InlineKeyboardButton("✅ Finish Import", callback_data="finish_import")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Store next URL
                self.json_import_state['next_url'] = next_url
                
                await update.message.reply_text(
                    response_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            else:
                response_text += "✅ <b>All pages imported!</b>"
                self.awaiting_json_import = False
                self.json_import_state = {}
                
                await update.message.reply_text(response_text, parse_mode='HTML')
            
        except json.JSONDecodeError as e:
            await update.message.reply_text(f"❌ Invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Import error: {e}")
            await update.message.reply_text(f"❌ Import failed: {str(e)}")

    async def cmd_follow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /follow <username>."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if not self.insta_client or not self.insta_client.is_logged_in:
            await update.message.reply_text("❌ Please /login first")
            return
        
        if not context.args:
            await update.message.reply_text(
                "📝 <b>Usage:</b> /follow &lt;username&gt;\n\n"
                "<b>Example:</b> /follow cristiano",
                parse_mode='HTML'
            )
            return
        
        username = context.args[0].replace('@', '')
        
        try:
            msg = await update.message.reply_text(
                f"🔍 <b>Looking up @{username}...</b>",
                parse_mode='HTML'
            )
            
            user_info = self.insta_client.client.user_info_by_username(username)
            user_id = user_info.pk
            
            await self.update_message(
                msg.message_id,
                f"👤 <b>Following @{username}</b>\n\n"
                f"⏱️ Waiting {config.MIN_ACTION_DELAY}-{config.MAX_ACTION_DELAY}s..."
            )
            
            success = self.insta_client.safe_follow(user_id)
            
            if success:
                stats = self.insta_client.get_stats()
                await self.update_message(
                    msg.message_id,
                    f"✅ <b>Followed @{username}</b>\n\n"
                    f"📊 <b>Today:</b>\n"
                    f"• Follows: {stats.get('follow', 0)}\n"
                    f"• Likes: {stats.get('like', 0)}"
                )
                
                self.db.add_follow_record(str(user_id), username, "manual")
                self.db.log_action('follow', str(user_id), True, "Manual follow")
            else:
                await self.update_message(
                    msg.message_id,
                    f"❌ <b>Failed to follow @{username}</b>"
                )
                
        except Exception as e:
            logger.error(f"Follow error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_unfollow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unfollow <username>."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if not self.insta_client or not self.insta_client.is_logged_in:
            await update.message.reply_text("❌ Please /login first")
            return
        
        if not context.args:
            await update.message.reply_text(
                "📝 <b>Usage:</b> /unfollow &lt;username&gt;",
                parse_mode='HTML'
            )
            return
        
        username = context.args[0].replace('@', '')
        
        try:
            msg = await update.message.reply_text(
                f"🔍 <b>Looking up @{username}...</b>",
                parse_mode='HTML'
            )
            
            user_info = self.insta_client.client.user_info_by_username(username)
            user_id = user_info.pk
            
            success = self.insta_client.safe_unfollow(user_id)
            
            if success:
                await self.update_message(
                    msg.message_id,
                    f"✅ <b>Unfollowed @{username}</b>"
                )
                
                self.db.add_unfollow_record(str(user_id))
                self.db.log_action('unfollow', str(user_id), True, "Manual unfollow")
            else:
                await self.update_message(
                    msg.message_id,
                    f"❌ <b>Failed to unfollow @{username}</b>"
                )
                
        except Exception as e:
            logger.error(f"Unfollow error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_like(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /like <post_url>."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if not self.insta_client or not self.insta_client.is_logged_in:
            await update.message.reply_text("❌ Please /login first")
            return
        
        if not context.args:
            await update.message.reply_text(
                "📝 <b>Usage:</b> /like &lt;post_url&gt;",
                parse_mode='HTML'
            )
            return
        
        post_url = context.args[0]
        
        try:
            media_id = self.insta_client.client.media_pk_from_url(post_url)
            success = self.insta_client.safe_like(media_id)
            
            if success:
                stats = self.insta_client.get_stats()
                await update.message.reply_text(
                    f"✅ <b>Post liked!</b>\n\n"
                    f"📊 Likes today: {stats.get('like', 0)}",
                    parse_mode='HTML'
                )
                self.db.log_action('like', str(media_id), True, "Manual like")
            else:
                await update.message.reply_text("❌ Failed to like")
                
        except Exception as e:
            logger.error(f"Like error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status."""
        if not self._check_admin(update.effective_user.id):
            return
        
        insta_status = "✅ Logged in" if (self.insta_client and self.insta_client.is_logged_in) else "❌ Not logged in"
        
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
            f"<b>Failed:</b> {stats.get('tasks_failed', 0)}"
        )
        
        await update.message.reply_text(text, parse_mode='HTML')

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats."""
        if not self._check_admin(update.effective_user.id):
            return
        
        try:
            db_stats = self.db.get_statistics(days=7)
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
                f"Likes: {client_stats.get('like', 0)}"
            )
            
            await update.message.reply_text(text, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Stats error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /report."""
        if not self._check_admin(update.effective_user.id):
            return
        
        try:
            db_stats = self.db.get_statistics(days=1)
            
            follows_pct = (db_stats.get('follow_count', 0) / config.RATE_LIMITS['follows_per_day']) * 100
            likes_pct = (db_stats.get('like_count', 0) / config.RATE_LIMITS['likes_per_day']) * 100
            
            text = (
                f"<b>📅 Daily Report</b>\n"
                f"<i>{datetime.now().strftime('%Y-%m-%d')}</i>\n\n"
                f"<b>👥 Follows:</b> {db_stats.get('follow_count', 0)}/{config.RATE_LIMITS['follows_per_day']} ({follows_pct:.0f}%)\n"
                f"<b>👍 Likes:</b> {db_stats.get('like_count', 0)}/{config.RATE_LIMITS['likes_per_day']} ({likes_pct:.0f}%)\n"
                f"<b>💬 Comments:</b> {db_stats.get('comment_count', 0)}/{config.RATE_LIMITS['comments_per_day']}\n"
                f"<b>👁️ Stories:</b> {db_stats.get('story_view_count', 0)}/{config.RATE_LIMITS['story_views_per_day']}\n"
                f"<b>🚫 Unfollows:</b> {db_stats.get('unfollows', 0)}/{config.RATE_LIMITS['unfollows_per_day']}"
            )
            
            await update.message.reply_text(text, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Report error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_start_scheduler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start_scheduler."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if not self.insta_client or not self.insta_client.is_logged_in:
            await update.message.reply_text("❌ Please /login first")
            return
        
        if not self.scheduler:
            await update.message.reply_text("❌ Scheduler not initialized")
            return
        
        if not self.scheduler.running:
            self.scheduler.start()
        
        if not self.modules:
            self.modules = {
                'follow': FollowFollowersOfFollowers(self.insta_client, self.scheduler),
                'stories': LikeStoriesOfFollowers(self.insta_client, self.scheduler),
                'comment': CommentEmoji(self.insta_client, self.scheduler),
                'unfollow': UnfollowAfterDelay(self.insta_client, self.scheduler)
            }
        
        keyboard = [
            [InlineKeyboardButton("👥 Follow Followers", callback_data="task_follow")],
            [InlineKeyboardButton("📸 View Stories", callback_data="task_stories")],
            [InlineKeyboardButton("👍 Like & Comment", callback_data="task_comment")],
            [InlineKeyboardButton("🚫 Unfollow Old", callback_data="task_unfollow")],
            [InlineKeyboardButton("▶️ All Tasks", callback_data="task_all")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚙️ <b>Select tasks:</b>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    async def cmd_stop_scheduler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop_scheduler."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if self.scheduler:
            self.scheduler.stop()
            await update.message.reply_text("⏹️ Scheduler stopped")
        else:
            await update.message.reply_text("❌ Not initialized")

    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pause."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if self.scheduler:
            self.scheduler.pause()
            await update.message.reply_text("⏸️ Paused")
        else:
            await update.message.reply_text("❌ Not initialized")

    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /resume."""
        if not self._check_admin(update.effective_user.id):
            return
        
        if self.scheduler:
            self.scheduler.resume()
            await update.message.reply_text("▶️ Resumed")
        else:
            await update.message.reply_text("❌ Not initialized")

    async def cmd_limits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /limits."""
        if not self._check_admin(update.effective_user.id):
            return
        
        limits = config.RATE_LIMITS
        text = (
            "<b>⚠️ Rate Limits</b>\n\n"
            f"<b>Follows:</b> {limits['follows_per_day']}/day, {limits['follows_per_hour']}/hour\n"
            f"<b>Likes:</b> {limits['likes_per_day']}/day, {limits['likes_per_hour']}/hour\n"
            f"<b>Comments:</b> {limits['comments_per_day']}/day\n"
            f"<b>Stories:</b> {limits['story_views_per_day']}/day\n"
            f"<b>Unfollows:</b> {limits['unfollows_per_day']}/day\n\n"
            f"<b>Delay:</b> {config.MIN_ACTION_DELAY}-{config.MAX_ACTION_DELAY}s\n"
            f"<b>Unfollow after:</b> {config.UNFOLLOW_AFTER_DAYS} days"
        )
        
        await update.message.reply_text(text, parse_mode='HTML')

    async def cmd_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /logs."""
        if not self._check_admin(update.effective_user.id):
            return
        
        try:
            with open(config.LOG_FILE, 'r') as f:
                lines = f.readlines()
                last_lines = lines[-50:] if len(lines) > 50 else lines
                log_text = ''.join(last_lines)
            
            if len(log_text) > 4000:
                log_text = "..." + log_text[-4000:]
            
            await update.message.reply_text(f"<pre>{log_text}</pre>", parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries."""
        query = update.callback_query
        await query.answer()
        
        if not self._check_admin(query.from_user.id):
            return
        
        data = query.data
        
        # Menu callbacks
        if data == "menu_login":
            keyboard = [
                [InlineKeyboardButton("🔑 Login", callback_data="action_login")],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🔑 <b>Login</b>\n\nUse /login command to authenticate",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        
        elif data == "menu_stats":
            keyboard = [
                [InlineKeyboardButton("📊 Status", callback_data="action_status")],
                [InlineKeyboardButton("📈 Stats", callback_data="action_stats")],
                [InlineKeyboardButton("📅 Report", callback_data="action_report")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📊 <b>Statistics</b>",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        
        elif data == "menu_automation":
            keyboard = [
                [InlineKeyboardButton("▶️ Start", callback_data="action_start_scheduler")],
                [InlineKeyboardButton("⏹️ Stop", callback_data="action_stop_scheduler")],
                [InlineKeyboardButton("⏸️ Pause", callback_data="action_pause")],
                [InlineKeyboardButton("▶️ Resume", callback_data="action_resume")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "⚙️ <b>Automation</b>",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        
        elif data == "menu_manual":
            await query.edit_message_text(
                "👤 <b>Manual Actions</b>\n\n"
                "Use commands:\n"
                "/follow &lt;username&gt;\n"
                "/unfollow &lt;username&gt;\n"
                "/like &lt;post_url&gt;",
                parse_mode='HTML'
            )
        
        elif data == "menu_import":
            keyboard = [
                [InlineKeyboardButton("📎 Import Followers", callback_data="action_import")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📎 <b>Manual Import</b>\n\n"
                "Import followers from Instagram GraphQL",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        
        elif data == "menu_info":
            keyboard = [
                [InlineKeyboardButton("⚠️ Limits", callback_data="action_limits")],
                [InlineKeyboardButton("📜 Logs", callback_data="action_logs")],
                [InlineKeyboardButton("❓Help", callback_data="action_help")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "ℹ️ <b>Info & Settings</b>",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        
        elif data == "back_menu":
            keyboard = [
                [InlineKeyboardButton("🔑 Login", callback_data="menu_login")],
                [InlineKeyboardButton("📊 Stats", callback_data="menu_stats")],
                [InlineKeyboardButton("⚙️ Automation", callback_data="menu_automation")],
                [InlineKeyboardButton("👤 Manual", callback_data="menu_manual")],
                [InlineKeyboardButton("📎 Import", callback_data="menu_import")],
                [InlineKeyboardButton("ℹ️ Info", callback_data="menu_info")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🏠 <b>Main Menu</b>",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        
        # Action callbacks
        elif data == "action_import":
            await query.message.reply_text(
                "Use /import_followers command to start manual import"
            )
        
        elif data == "get_next_page":
            next_url = self.json_import_state.get('next_url', '')
            if next_url:
                await query.message.reply_text(
                    f"<b>🔗 Next Page URL:</b>\n\n"
                    f"<code>{next_url}</code>\n\n"
                    "Copy URL, get JSON, and send it here",
                    parse_mode='HTML'
                )
        
        elif data == "finish_import":
            total = self.json_import_state.get('total_imported', 0)
            pages = self.json_import_state.get('pages', 0)
            
            await query.message.reply_text(
                f"✅ <b>Import Finished!</b>\n\n"
                f"📊 Total: {total} followers\n"
                f"📄 Pages: {pages}",
                parse_mode='HTML'
            )
            
            self.awaiting_json_import = False
            self.json_import_state = {}
        
        # Task callbacks
        elif data == "task_follow":
            await query.edit_message_text("▶️ Starting follow module...")
            self.modules['follow'].run()
            await query.message.reply_text("✅ Follow module started")
        
        elif data == "task_stories":
            await query.edit_message_text("▶️ Starting stories module...")
            self.modules['stories'].run()
            await query.message.reply_text("✅ Stories module started")
        
        elif data == "task_comment":
            await query.edit_message_text("▶️ Starting comment module...")
            self.modules['comment'].run()
            await query.message.reply_text("✅ Comment module started")
        
        elif data == "task_unfollow":
            await query.edit_message_text("▶️ Starting unfollow module...")
            self.modules['unfollow'].run()
            await query.message.reply_text("✅ Unfollow module started")
        
        elif data == "task_all":
            await query.edit_message_text("▶️ Starting all modules...")
            self.modules['follow'].run()
            self.modules['stories'].run()
            self.modules['comment'].run()
            self.modules['unfollow'].run()
            await query.message.reply_text("✅ All modules started")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages."""
        if not self._check_admin(update.effective_user.id):
            return
        
        text = update.message.text
        
        # Check for 2FA
        if self.awaiting_2fa:
            code = text.strip()
            
            if self.insta_client:
                success = self.insta_client.verify_2fa(code)
                
                if success:
                    self.awaiting_2fa = False
                    await update.message.reply_text("✅ 2FA successful!")
                    
                    self.modules = {
                        'follow': FollowFollowersOfFollowers(self.insta_client, self.scheduler),
                        'stories': LikeStoriesOfFollowers(self.insta_client, self.scheduler),
                        'comment': CommentEmoji(self.insta_client, self.scheduler),
                        'unfollow': UnfollowAfterDelay(self.insta_client, self.scheduler)
                    }
                else:
                    await update.message.reply_text("❌ Invalid code")
        
        # Check for JSON import
        elif self.awaiting_json_import:
            # Try to parse as JSON
            try:
                await self._import_followers_json(update, text)
            except:
                await update.message.reply_text(
                    "❌ Invalid JSON. Send file or paste valid JSON."
                )
        
        else:
            text = (
                "ℹ️ <b>I don't understand.</b>\n\n"
                "📚 Use /menu or /help"
            )
            await update.message.reply_text(text, parse_mode='HTML')

    def run(self):
        """Start the bot."""
        logger.info("Starting Telegram bot...")
        self.app.run_polling()
