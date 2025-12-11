"""Module to view and like stories of followers."""
import random
import logging
from typing import List

from core.insta_client import InstagramClient
from core.scheduler import TaskScheduler, TaskPriority
from includes.database import Database
from includes.logger import setup_logger

logger = setup_logger(__name__)


class LikeStoriesOfFollowers:
    """View and interact with stories of followers."""

    def __init__(self, insta_client: InstagramClient, scheduler: TaskScheduler):
        """Initialize module.
        
        Args:
            insta_client: Instagram client instance
            scheduler: Task scheduler instance
        """
        self.client = insta_client
        self.scheduler = scheduler
        self.db = Database()

    def run(self, num_followers: int = 30, max_stories: int = 50):
        """View stories of followers.
        
        Args:
            num_followers: Number of followers to check
            max_stories: Maximum stories to view
        """
        try:
            logger.info("Starting like stories of followers module")
            
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
            
            # Randomize order
            random.shuffle(followers)
            
            tasks = []
            story_count = 0
            
            for follower in followers:
                if story_count >= max_stories:
                    break
                
                follower_id = follower.pk
                follower_username = follower.username
                
                # Get user stories
                stories = self.client.get_user_stories(follower_id)
                
                if not stories:
                    continue
                
                logger.info(f"Found {len(stories)} stories from @{follower_username}")
                
                # View random subset of stories
                num_to_view = min(len(stories), random.randint(1, 3))
                stories_to_view = random.sample(stories, num_to_view)
                
                for story in stories_to_view:
                    if story_count >= max_stories:
                        break
                    
                    tasks.append({
                        'func': self._view_story,
                        'task_type': 'story_view',
                        'priority': TaskPriority.LOW,
                        'args': (story.pk, follower_username)
                    })
                    
                    story_count += 1
            
            if tasks:
                # Schedule with randomization
                self.scheduler.schedule_batch(
                    tasks,
                    randomize_order=True,
                    spread_over_minutes=30  # Spread over 30 minutes
                )
                logger.info(f"Scheduled {len(tasks)} story view tasks")
            else:
                logger.info("No stories found")
                
        except Exception as e:
            logger.error(f"Story viewing module error: {e}", exc_info=True)

    def _view_story(self, story_id: str, username: str):
        """View a story.
        
        Args:
            story_id: Story ID
            username: Story owner username
        """
        try:
            success = self.client.safe_view_story(story_id)
            
            if success:
                self.db.log_action('story_view', story_id, True, f"Viewed story from @{username}")
                logger.debug(f"Viewed story from @{username}")
            else:
                self.db.log_action('story_view', story_id, False, f"Failed to view story from @{username}")
                
        except Exception as e:
            logger.error(f"Error viewing story {story_id}: {e}")
            self.db.log_action('story_view', story_id, False, str(e))
