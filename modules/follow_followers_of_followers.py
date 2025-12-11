"""Module to follow followers of your followers."""
import random
import logging
from typing import List, Set

from core.insta_client import InstagramClient
from core.scheduler import TaskScheduler, TaskPriority
from includes.database import Database
from includes.logger import setup_logger
import config

logger = setup_logger(__name__)


class FollowFollowersOfFollowers:
    """Follow followers of your followers to expand reach."""

    def __init__(self, insta_client: InstagramClient, scheduler: TaskScheduler):
        """Initialize module.
        
        Args:
            insta_client: Instagram client instance
            scheduler: Task scheduler instance
        """
        self.client = insta_client
        self.scheduler = scheduler
        self.db = Database()
        self.already_followed: Set[int] = set()

    def run(
        self,
        num_followers_to_check: int = 10,
        followers_per_user: int = 5,
        max_total_follows: int = 30
    ):
        """Execute follow strategy.
        
        Args:
            num_followers_to_check: Number of your followers to check
            followers_per_user: Number of their followers to follow
            max_total_follows: Maximum total follows in this run
        """
        try:
            logger.info("Starting follow followers of followers module")
            
            my_user_id = self.client.get_my_user_id()
            if not my_user_id:
                logger.error("Could not get user ID")
                return
            
            # Get my followers
            logger.info(f"Fetching {num_followers_to_check} of your followers...")
            my_followers = self.client.get_user_followers(my_user_id, num_followers_to_check)
            
            if not my_followers:
                logger.warning("No followers found")
                return
            
            logger.info(f"Found {len(my_followers)} followers")
            
            # Randomly select followers to check
            random.shuffle(my_followers)
            
            tasks = []
            total_targets = 0
            
            for follower in my_followers:
                if total_targets >= max_total_follows:
                    break
                
                follower_id = follower.pk
                follower_username = follower.username
                
                logger.info(f"Checking followers of @{follower_username}...")
                
                # Get their followers
                their_followers = self.client.get_user_followers(
                    follower_id,
                    followers_per_user * 2  # Get extra to filter
                )
                
                if not their_followers:
                    continue
                
                # Filter and select targets
                targets = self._filter_targets(their_followers, followers_per_user)
                
                for target in targets:
                    if total_targets >= max_total_follows:
                        break
                    
                    # Schedule follow task
                    tasks.append({
                        'func': self._follow_user,
                        'task_type': 'follow',
                        'priority': TaskPriority.NORMAL,
                        'args': (target.pk, target.username, f"follower_of_{follower_username}")
                    })
                    
                    total_targets += 1
            
            if tasks:
                # Schedule tasks with randomization
                self.scheduler.schedule_batch(
                    tasks,
                    randomize_order=True,
                    spread_over_minutes=60  # Spread over 1 hour
                )
                logger.info(f"Scheduled {len(tasks)} follow tasks")
            else:
                logger.info("No suitable targets found")
                
        except Exception as e:
            logger.error(f"Follow module error: {e}", exc_info=True)

    def _filter_targets(self, users: List, max_count: int) -> List:
        """Filter and select target users.
        
        Args:
            users: List of user objects
            max_count: Maximum users to return
            
        Returns:
            List of filtered users
        """
        filtered = []
        
        for user in users:
            # Skip if already followed
            if user.pk in self.already_followed:
                continue
            
            # Skip private accounts
            if user.is_private:
                continue
            
            # Skip verified accounts (celebrities)
            if getattr(user, 'is_verified', False):
                continue
            
            # Skip accounts with suspicious follower ratios
            follower_count = getattr(user, 'follower_count', 0)
            following_count = getattr(user, 'following_count', 1)
            
            if follower_count > 10000:  # Too popular
                continue
            
            if following_count < 10:  # Inactive or bot
                continue
            
            ratio = following_count / follower_count if follower_count > 0 else 999
            if ratio > 5 or ratio < 0.1:  # Suspicious ratio
                continue
            
            filtered.append(user)
            
            if len(filtered) >= max_count:
                break
        
        random.shuffle(filtered)
        return filtered[:max_count]

    def _follow_user(self, user_id: int, username: str, source: str):
        """Follow a user and record.
        
        Args:
            user_id: Instagram user ID
            username: Instagram username
            source: Source of follow
        """
        try:
            success = self.client.safe_follow(user_id)
            
            if success:
                self.already_followed.add(user_id)
                self.db.add_follow_record(str(user_id), username, source)
                self.db.log_action('follow', str(user_id), True, f"Followed @{username} from {source}")
                logger.info(f"Followed @{username}")
            else:
                self.db.log_action('follow', str(user_id), False, f"Failed to follow @{username}")
                
        except Exception as e:
            logger.error(f"Error following user {user_id}: {e}")
            self.db.log_action('follow', str(user_id), False, str(e))
