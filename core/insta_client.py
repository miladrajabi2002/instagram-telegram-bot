"""Instagram client wrapper with safe API calls and session management."""
import time
import random
import logging
import json
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import quote

from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired, ChallengeRequired, TwoFactorRequired,
    RateLimitError, ClientError, PleaseWaitFewMinutes
)

import config
from includes.database import Database
from includes.cache import Cache
from includes.security import encrypt_data, decrypt_data
from includes.logger import setup_logger

logger = setup_logger(__name__)


class InstagramClient:
    """Safe Instagram client with rate limiting and error handling."""

    def __init__(self, username: str, password: str, telegram_notifier=None):
        """Initialize Instagram client.
        
        Args:
            username: Instagram username
            password: Instagram password
            telegram_notifier: Function to send Telegram notifications
        """
        self.username = username
        self.password = password
        self.telegram_notifier = telegram_notifier
        self.client = Client()
        
        # Set human-like delays (5-15 seconds)
        self.client.delay_range = [5, 15]
        
        # Set request timeout
        self.client.request_timeout = 10
        
        self.db = Database()
        self.cache = Cache()
        self.session_file = config.SESSION_DIR / f"{username}_session.json"
        self.is_logged_in = False
        
        # Rate limiting tracking
        self.last_action_time = None
        self.action_count = {'follow': 0, 'like': 0, 'comment': 0, 'story_view': 0}
        self.action_timestamps = {'follow': [], 'like': [], 'comment': [], 'story_view': []}

    def login(self) -> bool:
        """Login to Instagram with session management.
        
        Returns:
            bool: True if login successful
        """
        try:
            # Try to load existing session
            if self._load_session():
                logger.info(f"✅ Loaded session for {self.username}")
                self.is_logged_in = True
                return True
            
            # New login
            logger.info(f"🔐 Attempting login for {self.username}")
            self.client.login(self.username, self.password)
            self._save_session()
            self.is_logged_in = True
            
            self._notify(f"✅ Successfully logged in to Instagram as {self.username}")
            logger.info(f"✅ Successfully logged in as {self.username}")
            return True
            
        except TwoFactorRequired:
            logger.warning("⚠️ 2FA required")
            self._notify("⚠️ 2FA required! Please provide the code via Telegram.")
            return False
            
        except ChallengeRequired as e:
            logger.warning(f"⚠️ Challenge required: {e}")
            self._notify(f"⚠️ Instagram challenge required!\n{str(e)}\nPlease verify via Instagram app.")
            return False
            
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            self._notify(f"❌ Login failed: {str(e)}")
            return False

    def verify_2fa(self, code: str) -> bool:
        """Verify 2FA code.
        
        Args:
            code: 2FA verification code
            
        Returns:
            bool: True if verification successful
        """
        try:
            # Use the correct method for instagrapi
            self.client.login(self.username, self.password, verification_code=code)
            self._save_session()
            self.is_logged_in = True
            self._notify("✅ 2FA verification successful!")
            logger.info("✅ 2FA verification successful")
            return True
        except Exception as e:
            logger.error(f"❌ 2FA verification failed: {e}")
            self._notify(f"❌ 2FA verification failed: {str(e)}")
            return False

    def _load_session(self) -> bool:
        """Load session from file.
        
        Returns:
            bool: True if session loaded successfully
        """
        try:
            if not self.session_file.exists():
                logger.debug("❌ Session file not found")
                return False
                
            logger.debug("📂 Loading session from file...")
            self.client.load_settings(self.session_file)
            self.client.login(self.username, self.password)
            
            # Verify session is valid
            logger.debug("🔍 Verifying session...")
            timeline = self.client.get_timeline_feed()
            logger.debug(f"✅ Session valid - Timeline has {len(timeline)} items")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to load session: {e}")
            if self.session_file.exists():
                logger.debug("🗑️ Deleting invalid session file")
                self.session_file.unlink()
            return False

    def _save_session(self):
        """Save session to file."""
        try:
            self.client.dump_settings(self.session_file)
            logger.info(f"💾 Session saved to {self.session_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save session: {e}")

    def _notify(self, message: str):
        """Send Telegram notification.
        
        Args:
            message: Notification message
        """
        if self.telegram_notifier:
            try:
                self.telegram_notifier(message)
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")

    def _wait_random_delay(self, min_delay: int = None, max_delay: int = None):
        """Wait for a random human-like delay.
        
        Args:
            min_delay: Minimum delay in seconds
            max_delay: Maximum delay in seconds
        """
        min_delay = min_delay or config.MIN_ACTION_DELAY
        max_delay = max_delay or config.MAX_ACTION_DELAY
        
        # Random delay between min and max
        delay = random.uniform(min_delay, max_delay)
        
        logger.info(f"⏱️ Waiting {delay:.1f} seconds before action...")
        time.sleep(delay)
        logger.info(f"✅ Delay complete, executing action now")

    def _check_rate_limit(self, action_type: str) -> bool:
        """Check if action exceeds rate limits.
        
        Args:
            action_type: Type of action (follow, like, comment, story_view)
            
        Returns:
            bool: True if within limits
        """
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Clean old timestamps
        self.action_timestamps[action_type] = [
            ts for ts in self.action_timestamps[action_type] if ts > day_ago
        ]
        
        # Check hourly limit
        hourly_count = sum(1 for ts in self.action_timestamps[action_type] if ts > hour_ago)
        hourly_limit = config.RATE_LIMITS.get(f"{action_type}s_per_hour", 999)
        
        if hourly_count >= hourly_limit:
            logger.warning(f"⚠️ Hourly rate limit reached for {action_type}: {hourly_count}/{hourly_limit}")
            self._notify(f"⚠️ Hourly rate limit reached for {action_type}. Pausing...")
            return False
        
        # Check daily limit
        daily_count = len(self.action_timestamps[action_type])
        daily_limit = config.RATE_LIMITS.get(f"{action_type}s_per_day", 9999)
        
        if daily_count >= daily_limit:
            logger.warning(f"⚠️ Daily rate limit reached for {action_type}: {daily_count}/{daily_limit}")
            self._notify(f"⚠️ Daily rate limit reached for {action_type}. Stopping...")
            return False
        
        return True

    def _record_action(self, action_type: str):
        """Record action timestamp for rate limiting.
        
        Args:
            action_type: Type of action
        """
        self.action_timestamps[action_type].append(datetime.now())
        self.action_count[action_type] += 1

    def _safe_api_call(self, func, *args, **kwargs) -> Optional[Any]:
        """Execute API call with retry and exponential backoff.
        
        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or None on failure
        """
        for attempt in range(config.MAX_RETRIES):
            try:
                logger.debug(f"📡 API call: {func.__name__}")
                result = func(*args, **kwargs)
                logger.debug(f"✅ API call successful: {func.__name__}")
                return result
                
            except RateLimitError as e:
                wait_time = config.RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(f"⚠️ Rate limit hit: {e}. Waiting {wait_time}s...")
                self._notify(f"⚠️ Instagram rate limit hit. Waiting {wait_time}s...")
                time.sleep(wait_time)
                
            except PleaseWaitFewMinutes as e:
                wait_time = 900  # 15 minutes
                logger.warning(f"⚠️ Instagram asks to wait: {e}. Waiting {wait_time}s...")
                self._notify(f"⚠️ Instagram requests wait. Pausing for 15 minutes...")
                time.sleep(wait_time)
                
            except ChallengeRequired as e:
                logger.error(f"❌ Challenge required: {e}")
                # Extract challenge URL if present
                challenge_url = "https://www.instagram.com/challenge/"
                self._notify(
                    f"🚨 <b>Instagram Challenge Required!</b>\n\n"
                    f"Please verify your account:\n"
                    f"{challenge_url}\n\n"
                    f"Open this link in your browser and complete the verification."
                )
                return None
                
            except LoginRequired as e:
                logger.error(f"❌ Login required: {e}")
                self._notify("⚠️ Session expired. Re-logging in...")
                if self.login():
                    continue
                return None
                
            except ClientError as e:
                error_msg = str(e)
                # Check if it's a challenge
                if 'challenge' in error_msg.lower():
                    logger.error(f"❌ Challenge detected in error: {error_msg[:100]}")
                    self._notify(
                        f"🚨 <b>Instagram Challenge Detected!</b>\n\n"
                        f"Please verify your account at:\n"
                        f"https://www.instagram.com/challenge/\n\n"
                        f"Complete the verification and try again."
                    )
                    return None
                
                logger.error(f"❌ Client error: {error_msg[:100]}")
                if attempt < config.MAX_RETRIES - 1:
                    wait_time = config.RETRY_DELAY_BASE * (2 ** attempt)
                    time.sleep(wait_time)
                else:
                    self._notify(f"❌ API call failed after {config.MAX_RETRIES} attempts")
                    return None
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Unexpected error: {error_msg[:100]}")
                self._notify(f"❌ Unexpected error: {error_msg[:200]}")
                return None
        
        return None

    # Safe API wrappers
    
    def safe_follow(self, user_id: int) -> bool:
        """Safely follow a user.
        
        Args:
            user_id: Instagram user ID
            
        Returns:
            bool: True if successful
        """
        if not self._check_rate_limit('follow'):
            return False
        
        logger.info(f"👤 Preparing to follow user {user_id}...")
        self._wait_random_delay()
        
        logger.info(f"📡 Sending follow request for user {user_id}...")
        result = self._safe_api_call(self.client.user_follow, user_id)
        
        if result:
            self._record_action('follow')
            logger.info(f"✅ Successfully followed user {user_id}")
            return True
        
        logger.error(f"❌ Failed to follow user {user_id}")
        return False

    def safe_unfollow(self, user_id: int) -> bool:
        """Safely unfollow a user.
        
        Args:
            user_id: Instagram user ID
            
        Returns:
            bool: True if successful
        """
        logger.info(f"👤 Preparing to unfollow user {user_id}...")
        self._wait_random_delay()
        
        result = self._safe_api_call(self.client.user_unfollow, user_id)
        
        if result:
            logger.info(f"✅ Successfully unfollowed user {user_id}")
            return True
        
        logger.error(f"❌ Failed to unfollow user {user_id}")
        return False

    def safe_like(self, media_id: str) -> bool:
        """Safely like a post.
        
        Args:
            media_id: Instagram media ID
            
        Returns:
            bool: True if successful
        """
        if not self._check_rate_limit('like'):
            return False
        
        logger.info(f"👍 Preparing to like media {media_id}...")
        self._wait_random_delay()
        
        result = self._safe_api_call(self.client.media_like, media_id)
        
        if result:
            self._record_action('like')
            logger.info(f"✅ Successfully liked media {media_id}")
            return True
        
        logger.error(f"❌ Failed to like media {media_id}")
        return False

    def safe_comment(self, media_id: str, text: str) -> bool:
        """Safely comment on a post.
        
        Args:
            media_id: Instagram media ID
            text: Comment text
            
        Returns:
            bool: True if successful
        """
        if not self._check_rate_limit('comment'):
            return False
        
        logger.info(f"💬 Preparing to comment on media {media_id}...")
        self._wait_random_delay(120, 300)  # Longer delay for comments
        
        result = self._safe_api_call(self.client.media_comment, media_id, text)
        
        if result:
            self._record_action('comment')
            logger.info(f"✅ Successfully commented on media {media_id}")
            return True
        
        logger.error(f"❌ Failed to comment on media {media_id}")
        return False

    def safe_view_story(self, story_id: str) -> bool:
        """Safely view a story.
        
        Args:
            story_id: Instagram story ID
            
        Returns:
            bool: True if successful
        """
        if not self._check_rate_limit('story_view'):
            return False
        
        logger.info(f"👁️ Preparing to view story {story_id}...")
        # Longer delay for stories to be more human-like
        self._wait_random_delay(15, 45)
        
        result = self._safe_api_call(self.client.story_seen, [story_id])
        
        if result:
            self._record_action('story_view')
            logger.info(f"✅ Viewed story {story_id}")
            return True
        
        logger.error(f"❌ Failed to view story {story_id}")
        return False

    # Helper methods with caching
    
    def get_user_followers(self, user_id: int, amount: int = 50) -> List[Dict]:
        """Get user followers with incremental caching using GraphQL.
        
        Args:
            user_id: Instagram user ID
            amount: Number of followers to fetch
            
        Returns:
            List of follower dictionaries
        """
        cache_key = f"followers_{user_id}_{amount}"
        
        # Try cache first (valid for 1 hour)
        cached = self.cache.get(cache_key, ttl=3600)
        if cached:
            logger.info(f"💾 Using cached {len(cached)} followers for user {user_id}")
            return cached
        
        # Fetch from GraphQL API with pagination
        logger.info(f"📡 Fetching up to {amount} followers for user {user_id}...")
        all_followers = []
        end_cursor = None
        page = 1
        
        try:
            while len(all_followers) < amount:
                logger.info(f"📄 Fetching page {page} (have {len(all_followers)}/{amount} so far)...")
                
                # Build GraphQL query URL
                variables = {
                    "id": str(user_id),
                    "include_reel": True,
                    "fetch_mutual": False,
                    "first": 12
                }
                
                if end_cursor:
                    variables["after"] = end_cursor
                
                # Use instagrapi's public_request method
                try:
                    data = self.client.public_graphql_request(
                        variables=variables,
                        query_hash="37479f2b8209594dde7facb0d904896a"
                    )
                except Exception as e:
                    # Check if challenge
                    error_str = str(e).lower()
                    if 'challenge' in error_str or 'jsondecode' in error_str:
                        logger.error("🚨 Challenge detected")
                        self._notify(
                            f"🚨 <b>Challenge Required!</b>\n\n"
                            f"Collected {len(all_followers)} followers before challenge.\n\n"
                            f"Verify at: https://www.instagram.com/challenge/"
                        )
                        break
                    raise
                
                # Parse response
                if not data or 'data' not in data:
                    logger.warning("⚠️ No data in response")
                    break
                
                user_data = data['data'].get('user', {})
                edge_followed_by = user_data.get('edge_followed_by', {})
                edges = edge_followed_by.get('edges', [])
                page_info = edge_followed_by.get('page_info', {})
                
                if not edges:
                    logger.info("✅ No more followers")
                    break
                
                # Convert to follower objects
                for edge in edges:
                    node = edge.get('node', {})
                    # Create a simple object-like dict
                    follower = type('obj', (object,), {
                        'pk': int(node.get('id')),
                        'username': node.get('username'),
                        'full_name': node.get('full_name', ''),
                        'profile_pic_url': node.get('profile_pic_url', ''),
                        'is_verified': node.get('is_verified', False)
                    })
                    all_followers.append(follower)
                
                logger.info(f"✅ Got {len(edges)} followers (total: {len(all_followers)})")
                
                # Save incrementally
                self.cache.set(cache_key, all_followers)
                for follower in edges:
                    node = follower.get('node', {})
                    self.db.add_follow_record(
                        node.get('id'),
                        node.get('username'),
                        "my_follower"
                    )
                logger.info(f"💾 Saved {len(edges)} followers (incremental)")
                
                # Check pagination
                if not page_info.get('has_next_page'):
                    logger.info("✅ Reached end of followers list")
                    break
                
                end_cursor = page_info.get('end_cursor')
                page += 1
                
                # Small delay between pages
                time.sleep(random.uniform(2, 5))
                
        except Exception as e:
            logger.error(f"❌ Error fetching followers: {str(e)[:100]}")
            self._notify(f"❌ Error: {str(e)[:200]}. Saved {len(all_followers)} followers.")
        
        # Final cache update
        if all_followers:
            self.cache.set(cache_key, all_followers)
            logger.info(f"💾 Final: {len(all_followers)} followers cached")
        
        return all_followers

    def get_user_following(self, user_id: int, amount: int = 50) -> List[Dict]:
        """Get users followed by user with caching.
        
        Args:
            user_id: Instagram user ID
            amount: Number of following to fetch
            
        Returns:
            List of following dictionaries
        """
        cache_key = f"following_{user_id}_{amount}"
        
        # Try cache first
        cached = self.cache.get(cache_key, ttl=3600)
        if cached:
            logger.info(f"💾 Using cached following for user {user_id}")
            return cached
        
        # Fetch from API
        logger.info(f"📡 Fetching {amount} following for user {user_id}...")
        result = self._safe_api_call(self.client.user_following, user_id, amount)
        following = list(result.values()) if result else []
        
        # Cache result
        if following:
            self.cache.set(cache_key, following)
            logger.info(f"💾 Cached {len(following)} following")
        
        return following

    def get_user_medias(self, user_id: int, amount: int = 20) -> List[Any]:
        """Get user media posts.
        
        Args:
            user_id: Instagram user ID
            amount: Number of posts to fetch
            
        Returns:
            List of media objects
        """
        result = self._safe_api_call(self.client.user_medias, user_id, amount)
        return result if result else []

    def get_user_stories(self, user_id: int) -> List[Any]:
        """Get user stories.
        
        Args:
            user_id: Instagram user ID
            
        Returns:
            List of story objects
        """
        logger.info(f"📖 Fetching stories for user {user_id}...")
        result = self._safe_api_call(self.client.user_stories, user_id)
        
        if result:
            logger.info(f"✅ Found {len(result)} stories")
        else:
            logger.info("ℹ️ No stories found")
        
        return result if result else []

    def get_my_user_id(self) -> Optional[int]:
        """Get authenticated user's ID.
        
        Returns:
            User ID or None
        """
        try:
            user_id = self.client.user_id
            logger.debug(f"👤 My user ID: {user_id}")
            return user_id
        except:
            return None

    def get_stats(self) -> Dict[str, int]:
        """Get current action statistics.
        
        Returns:
            Dictionary with action counts
        """
        return self.action_count.copy()
