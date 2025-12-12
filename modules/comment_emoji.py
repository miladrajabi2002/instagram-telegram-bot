"""Module to like and comment on followers' posts."""
import logging
import random
from typing import List

import config
from includes.logger import setup_logger

logger = setup_logger(__name__)

# Emoji comments
EMOJI_COMMENTS = [
    "❤️",
    "🔥",
    "😍",
    "👏",
    "✨",
    "💯",
    "👍",
    "🙌",
    "❤️🔥",
    "✨✨",
    "🔥🔥",
    "😍😍",
]


class CommentEmoji:
    """Like and comment on followers' posts."""

    def __init__(self, insta_client, scheduler):
        """Initialize module.
        
        Args:
            insta_client: Instagram client instance
            scheduler: Task scheduler instance
        """
        self.client = insta_client
        self.scheduler = scheduler
        self.module_name = "comment_emoji"

    def run(self):
        """Schedule the like and comment task."""
        logger.info("Starting comment emoji module")
        
        # Schedule task
        task = {
            'type': 'comment',
            'function': self._execute,
            'interval': config.TASK_INTERVALS.get('comment', 3600)  # 1 hour
        }
        
        self.scheduler.add_task(task)
        logger.info("Comment task scheduled")

    def _execute(self):
        """Execute the like and comment logic."""
        logger.info("Executing comment emoji task")
        
        # Get followers from DATABASE (not API!)
        logger.info("💾 Getting followers from database...")
        followers = self.client.get_followers_from_db(limit=15)
        
        if not followers:
            logger.warning("⚠️ No followers in database")
            return
        
        logger.info(f"Got {len(followers)} followers from database")
        
        # Randomly select some followers
        num_to_interact = min(8, len(followers))
        selected_followers = random.sample(followers, num_to_interact)
        
        logger.info(f"Selected {num_to_interact} followers to interact with")
        
        likes_count = 0
        comments_count = 0
        
        for follower in selected_followers:
            try:
                # Get recent posts
                medias = self.client.get_user_medias(follower.pk, amount=3)
                
                if not medias:
                    logger.debug(f"No posts for {follower.username}")
                    continue
                
                logger.info(f"📸 User {follower.username} has {len(medias)} recent posts")
                
                # Like and optionally comment on first post
                media = medias[0]
                
                # Like post
                if self.client.safe_like(media.pk):
                    likes_count += 1
                    logger.info(f"✅ Liked post from {follower.username}")
                    
                    self.client.db.log_action(
                        'like',
                        str(media.pk),
                        True,
                        f"Liked post from {follower.username}"
                    )
                    
                    # 30% chance to comment emoji
                    if random.random() < 0.3:
                        emoji = random.choice(EMOJI_COMMENTS)
                        
                        if self.client.safe_comment(media.pk, emoji):
                            comments_count += 1
                            logger.info(f"✅ Commented '{emoji}' on {follower.username}'s post")
                            
                            self.client.db.log_action(
                                'comment',
                                str(media.pk),
                                True,
                                f"Commented on {follower.username}'s post"
                            )
                        else:
                            logger.warning(f"Failed to comment on {follower.username}'s post")
                else:
                    logger.warning(f"Failed to like {follower.username}'s post")
                    
            except Exception as e:
                logger.error(f"Error processing posts for {follower.username}: {e}")
                continue
        
        logger.info(f"✅ Like/Comment complete. Liked: {likes_count}, Commented: {comments_count}")
