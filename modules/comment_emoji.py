"""Module to comment emojis on posts."""
import random
import logging
from typing import List

from core.insta_client import InstagramClient
from core.scheduler import TaskScheduler, TaskPriority
from includes.database import Database
from includes.logger import setup_logger
import config

logger = setup_logger(__name__)


class CommentEmoji:
    """Leave emoji comments on posts."""

    def __init__(self, insta_client: InstagramClient, scheduler: TaskScheduler):
        """Initialize module.
        
        Args:
            insta_client: Instagram client instance
            scheduler: Task scheduler instance
        """
        self.client = insta_client
        self.scheduler = scheduler
        self.db = Database()

    def run(self, num_followers: int = 20, posts_per_user: int = 1, max_comments: int = 15):
        """Comment on followers' posts.
        
        Args:
            num_followers: Number of followers to check
            posts_per_user: Number of posts per user to comment on
            max_comments: Maximum total comments
        """
        try:
            logger.info("Starting emoji comment module")
            
            my_user_id = self.client.get_my_user_id()
            if not my_user_id:
                logger.error("Could not get user ID")
                return
            
            # Get followers
            logger.info(f"Fetching {num_followers} followers...")
            followers = self.client.get_user_followers(my_user_id, num_followers)
            
            if not followers:
                logger.warning("No followers found")
                return
            
            # Randomize
            random.shuffle(followers)
            
            tasks = []
            comment_count = 0
            
            for follower in followers:
                if comment_count >= max_comments:
                    break
                
                follower_id = follower.pk
                follower_username = follower.username
                
                # Get recent posts
                medias = self.client.get_user_medias(follower_id, posts_per_user * 2)
                
                if not medias:
                    continue
                
                # Select posts to comment on
                posts_to_comment = random.sample(medias, min(len(medias), posts_per_user))
                
                for media in posts_to_comment:
                    if comment_count >= max_comments:
                        break
                    
                    # Select random emoji
                    emoji = random.choice(config.EMOJI_COMMENTS)
                    
                    # Occasionally use multiple emojis
                    if random.random() < 0.3:  # 30% chance
                        emoji += random.choice(config.EMOJI_COMMENTS)
                    
                    tasks.append({
                        'func': self._comment_on_post,
                        'task_type': 'comment',
                        'priority': TaskPriority.NORMAL,
                        'args': (media.pk, emoji, follower_username)
                    })
                    
                    comment_count += 1
            
            if tasks:
                # Schedule with longer delays
                self.scheduler.schedule_batch(
                    tasks,
                    randomize_order=True,
                    spread_over_minutes=90  # Spread over 90 minutes
                )
                logger.info(f"Scheduled {len(tasks)} comment tasks")
            else:
                logger.info("No posts found to comment on")
                
        except Exception as e:
            logger.error(f"Comment module error: {e}", exc_info=True)

    def _comment_on_post(self, media_id: str, text: str, username: str):
        """Comment on a post.
        
        Args:
            media_id: Media ID
            text: Comment text
            username: Post owner username
        """
        try:
            success = self.client.safe_comment(media_id, text)
            
            if success:
                self.db.log_action('comment', media_id, True, f"Commented '{text}' on @{username}'s post")
                logger.info(f"Commented on @{username}'s post")
            else:
                self.db.log_action('comment', media_id, False, f"Failed to comment on @{username}'s post")
                
        except Exception as e:
            logger.error(f"Error commenting on post {media_id}: {e}")
            self.db.log_action('comment', media_id, False, str(e))
