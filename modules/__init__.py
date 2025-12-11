"""Automation modules for Instagram tasks."""

from .follow_followers_of_followers import FollowFollowersOfFollowers
from .like_stories_of_followers import LikeStoriesOfFollowers
from .comment_emoji import CommentEmoji
from .unfollow_after_delay import UnfollowAfterDelay

__all__ = [
    'FollowFollowersOfFollowers',
    'LikeStoriesOfFollowers',
    'CommentEmoji',
    'UnfollowAfterDelay'
]
