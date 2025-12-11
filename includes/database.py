"""Database connection and operations."""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager

import config
from .logger import setup_logger

logger = setup_logger(__name__)


class Database:
    """MySQL database handler."""

    def __init__(self):
        """Initialize database connection."""
        self.config = config.DB_CONFIG
        self.connection = None

    @contextmanager
    def get_connection(self):
        """Get database connection context manager.
        
        Yields:
            MySQL connection
        """
        connection = None
        try:
            connection = mysql.connector.connect(**self.config)
            yield connection
            connection.commit()
        except Error as e:
            logger.error(f"Database error: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()

    def execute_query(self, query: str, params: tuple = None) -> bool:
        """Execute a query without returning results.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            bool: True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                cursor.close()
            return True
        except Error as e:
            logger.error(f"Query execution failed: {e}")
            return False

    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch single row.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Dictionary with row data or None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, params or ())
                result = cursor.fetchone()
                cursor.close()
                return result
        except Error as e:
            logger.error(f"Fetch one failed: {e}")
            return None

    def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        """Fetch all rows.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            List of dictionaries with row data
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, params or ())
                results = cursor.fetchall()
                cursor.close()
                return results
        except Error as e:
            logger.error(f"Fetch all failed: {e}")
            return []

    # Logging methods

    def log_action(self, action_type: str, target_id: str, success: bool, details: str = None):
        """Log an automation action.
        
        Args:
            action_type: Type of action (follow, like, comment, etc.)
            target_id: Target user/media ID
            success: Whether action succeeded
            details: Additional details
        """
        query = """
            INSERT INTO action_logs (action_type, target_id, success, details, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """
        self.execute_query(query, (action_type, target_id, success, details, datetime.now()))

    def get_action_count(self, action_type: str, hours: int = 24) -> int:
        """Get action count for time period.
        
        Args:
            action_type: Type of action
            hours: Time period in hours
            
        Returns:
            int: Action count
        """
        query = """
            SELECT COUNT(*) as count FROM action_logs
            WHERE action_type = %s AND success = TRUE
            AND created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
        """
        result = self.fetch_one(query, (action_type, hours))
        return result['count'] if result else 0

    # Follow tracking

    def add_follow_record(self, user_id: str, username: str, source: str = None):
        """Add follow record.
        
        Args:
            user_id: Instagram user ID
            username: Instagram username
            source: Source of follow (e.g., 'followers_of_followers')
        """
        query = """
            INSERT INTO follows (user_id, username, followed_at, source)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE followed_at = VALUES(followed_at)
        """
        self.execute_query(query, (user_id, username, datetime.now(), source))

    def get_users_to_unfollow(self, days: int) -> List[Dict]:
        """Get users to unfollow after specified days.
        
        Args:
            days: Number of days since follow
            
        Returns:
            List of user dictionaries
        """
        query = """
            SELECT user_id, username FROM follows
            WHERE unfollowed_at IS NULL
            AND followed_at <= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY followed_at ASC
        """
        return self.fetch_all(query, (days,))

    def mark_unfollowed(self, user_id: str):
        """Mark user as unfollowed.
        
        Args:
            user_id: Instagram user ID
        """
        query = "UPDATE follows SET unfollowed_at = %s WHERE user_id = %s"
        self.execute_query(query, (datetime.now(), user_id))

    # Settings

    def save_setting(self, key: str, value: str):
        """Save a setting.
        
        Args:
            key: Setting key
            value: Setting value
        """
        query = """
            INSERT INTO settings (setting_key, setting_value, updated_at)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value), updated_at = VALUES(updated_at)
        """
        self.execute_query(query, (key, value, datetime.now()))

    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a setting value.
        
        Args:
            key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value or default
        """
        query = "SELECT setting_value FROM settings WHERE setting_key = %s"
        result = self.fetch_one(query, (key,))
        return result['setting_value'] if result else default

    # Statistics

    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get automation statistics.
        
        Args:
            days: Number of days to include
            
        Returns:
            Dictionary with statistics
        """
        stats = {}
        
        # Action counts by type
        query = """
            SELECT action_type, COUNT(*) as count
            FROM action_logs
            WHERE success = TRUE AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY action_type
        """
        results = self.fetch_all(query, (days,))
        for row in results:
            stats[f"{row['action_type']}_count"] = row['count']
        
        # Follow/unfollow stats
        query = "SELECT COUNT(*) as count FROM follows WHERE unfollowed_at IS NULL"
        result = self.fetch_one(query)
        stats['active_follows'] = result['count'] if result else 0
        
        query = """
            SELECT COUNT(*) as count FROM follows
            WHERE unfollowed_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """
        result = self.fetch_one(query, (days,))
        stats['unfollows'] = result['count'] if result else 0
        
        return stats
