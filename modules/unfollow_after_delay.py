"""Module to unfollow users after a delay period."""
import logging

from core.insta_client import InstagramClient
from core.scheduler import TaskScheduler, TaskPriority
from includes.database import Database
from includes.logger import setup_logger
import config

logger = setup_logger(__name__)


class UnfollowAfterDelay:
    """Unfollow users after specified delay."""

    def __init__(self, insta_client: InstagramClient, scheduler: TaskScheduler):
        """Initialize module.
        
        Args:
            insta_client: Instagram client instance
            scheduler: Task scheduler instance
        """
        self.client = insta_client
        self.scheduler = scheduler
        self.db = Database()

    def run(self, max_unfollows: int = 30):
        """Execute unfollow strategy.
        
        Args:
            max_unfollows: Maximum unfollows in this run
        """
        try:
            logger.info("Starting unfollow after delay module")
            
            # Get users to unfollow
            users_to_unfollow = self.db.get_users_to_unfollow(config.UNFOLLOW_AFTER_DAYS)
            
            if not users_to_unfollow:
                logger.info("No users to unfollow")
                return
            
            logger.info(f"Found {len(users_to_unfollow)} users to unfollow")
            
            # Limit to max_unfollows
            users_to_unfollow = users_to_unfollow[:max_unfollows]
            
            tasks = []
            for user in users_to_unfollow:
                tasks.append({
                    'func': self._unfollow_user,
                    'task_type': 'unfollow',
                    'priority': TaskPriority.LOW,
                    'args': (user['user_id'], user['username'])
                })
            
            if tasks:
                # Schedule with randomization
                self.scheduler.schedule_batch(
                    tasks,
                    randomize_order=True,
                    spread_over_minutes=60  # Spread over 1 hour
                )
                logger.info(f"Scheduled {len(tasks)} unfollow tasks")
                
        except Exception as e:
            logger.error(f"Unfollow module error: {e}", exc_info=True)

    def _unfollow_user(self, user_id: str, username: str):
        """Unfollow a user.
        
        Args:
            user_id: Instagram user ID
            username: Instagram username
        """
        try:
            success = self.client.safe_unfollow(int(user_id))
            
            if success:
                self.db.mark_unfollowed(user_id)
                self.db.log_action('unfollow', user_id, True, f"Unfollowed @{username}")
                logger.info(f"Unfollowed @{username}")
            else:
                self.db.log_action('unfollow', user_id, False, f"Failed to unfollow @{username}")
                
        except Exception as e:
            logger.error(f"Error unfollowing user {user_id}: {e}")
            self.db.log_action('unfollow', user_id, False, str(e))
