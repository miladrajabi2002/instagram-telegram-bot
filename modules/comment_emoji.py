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
        """Execute the like and comment logic directly."""
        logger.info("Starting comment emoji module")
        
        try:
            self._execute()
            logger.info("✅ Comment emoji module completed")
        except Exception as e:
            logger.error(f"❌ Comment emoji module failed: {e}", exc_info=True)

    def _execute(self):
        """Execute the like and comment logic."""
        logger.info("Executing comment emoji task")
        
        # Get followers from DATABASE (not API!)
        logger.info("📂 Getting followers from database...")
        followers = self.client.get_followers_from_db(limit=15)
        
        if not followers:
            logger.warning("⚠️ No followers in database")
            self.client._notify(
                "⚠️ <b>No followers found!</b>\n\n"
                "Please use /import_followers to add followers."
            )
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
                
                logger.info(f"📷 User {follower.username} has {len(medias)} recent posts")
                
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
        
        if likes_count > 0 or comments_count > 0:
            self.client._notify(
                f"✅ <b>Like/Comment Module Complete</b>\n\n"
                f"❤️ Likes: {likes_count}\n"
                f"💬 Comments: {comments_count}\n"
                f"👥 Interacted with {num_to_interact} followers"
            )
