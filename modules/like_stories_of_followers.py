"""Module to view and like stories of followers."""
import logging
import random
from typing import List

import config
from includes.logger import setup_logger

logger = setup_logger(__name__)


class LikeStoriesOfFollowers:
    """View and like stories of your followers."""

    def __init__(self, insta_client, scheduler):
        """Initialize module.
        
        Args:
            insta_client: Instagram client instance
            scheduler: Task scheduler instance
        """
        self.client = insta_client
        self.scheduler = scheduler
        self.module_name = "like_stories"

    def run(self):
        """Execute the story viewing logic directly."""
        logger.info("Starting like stories of followers module")
        
        try:
            self._execute()
            logger.info("✅ Like stories module completed")
        except Exception as e:
            logger.error(f"❌ Like stories module failed: {e}", exc_info=True)

    def _execute(self):
        """Execute the story viewing logic."""
        logger.info("Executing like stories task")
        
        # Get followers from DATABASE (not API!)
        logger.info("📂 Getting followers from database...")
        followers = self.client.get_followers_from_db(limit=20)
        
        if not followers:
            logger.warning("⚠️ No followers in database")
            self.client._notify(
                "⚠️ <b>No followers found!</b>\n\n"
                "Please use /import_followers to add followers."
            )
            return
        
        logger.info(f"Got {len(followers)} followers from database")
        
        # Randomly select some followers
        num_to_check = min(10, len(followers))
        selected_followers = random.sample(followers, num_to_check)
        
        logger.info(f"Selected {num_to_check} followers to check stories")
        
        stories_viewed = 0
        
        for follower in selected_followers:
            try:
                # Get stories
                stories = self.client.get_user_stories(follower.pk)
                
                if stories:
                    logger.info(f"📖 User {follower.username} has {len(stories)} stories")
                    
                    # View some stories (not all)
                    num_to_view = min(3, len(stories))
                    
                    for story in stories[:num_to_view]:
                        success = self.client.safe_view_story(story.pk)
                        
                        if success:
                            stories_viewed += 1
                            logger.info(f"✅ Viewed story from {follower.username}")
                            
                            # Log to database
                            self.client.db.log_action(
                                'story_view',
                                str(follower.pk),
                                True,
                                f"Viewed story from {follower.username}"
                            )
                        else:
                            logger.warning(f"Failed to view story from {follower.username}")
                            break
                else:
                    logger.debug(f"No stories for {follower.username}")
                    
            except Exception as e:
                logger.error(f"Error processing stories for {follower.username}: {e}")
                continue
        
        logger.info(f"✅ Story viewing complete. Viewed {stories_viewed} stories")
        
        if stories_viewed > 0:
            self.client._notify(
                f"✅ <b>Stories Module Complete</b>\n\n"
                f"👁️ Viewed {stories_viewed} stories from {num_to_check} followers"
            )
