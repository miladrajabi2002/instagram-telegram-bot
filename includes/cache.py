"""Simple cache system for Instagram data."""
import json
import time
from pathlib import Path
from typing import Optional, Any, Dict
from datetime import datetime, timedelta

import config
from includes.logger import setup_logger

logger = setup_logger(__name__)


class Cache:
    """File-based cache with TTL support."""
    
    def __init__(self, cache_dir: Path = None):
        """Initialize cache.
        
        Args:
            cache_dir: Directory for cache files
        """
        self.cache_dir = cache_dir or (config.BASE_DIR / 'cache')
        self.cache_dir.mkdir(exist_ok=True)
        
    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key.
        
        Args:
            key: Cache key
            
        Returns:
            Path to cache file
        """
        # Sanitize key for filename
        safe_key = key.replace('/', '_').replace(':', '_')
        return self.cache_dir / f"{safe_key}.json"
    
    def get(self, key: str, ttl: int = 3600) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            Cached value or None if expired/missing
        """
        cache_file = self._get_cache_file(key)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Check if expired
            cached_at = datetime.fromisoformat(data['cached_at'])
            if datetime.now() - cached_at > timedelta(seconds=ttl):
                logger.debug(f"Cache expired for key: {key}")
                cache_file.unlink()  # Delete expired cache
                return None
            
            logger.debug(f"Cache hit for key: {key}")
            return data['value']
            
        except Exception as e:
            logger.error(f"Error reading cache for {key}: {e}")
            return None
    
    def set(self, key: str, value: Any):
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
        """
        cache_file = self._get_cache_file(key)
        
        try:
            data = {
                'cached_at': datetime.now().isoformat(),
                'value': value
            }
            
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Cached value for key: {key}")
            
        except Exception as e:
            logger.error(f"Error writing cache for {key}: {e}")
    
    def delete(self, key: str):
        """Delete value from cache.
        
        Args:
            key: Cache key
        """
        cache_file = self._get_cache_file(key)
        
        if cache_file.exists():
            cache_file.unlink()
            logger.debug(f"Deleted cache for key: {key}")
    
    def clear(self):
        """Clear all cache."""
        for cache_file in self.cache_dir.glob('*.json'):
            cache_file.unlink()
        logger.info("Cache cleared")
    
    def clear_expired(self, ttl: int = 3600):
        """Clear expired cache entries.
        
        Args:
            ttl: Time to live in seconds
        """
        count = 0
        for cache_file in self.cache_dir.glob('*.json'):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                cached_at = datetime.fromisoformat(data['cached_at'])
                if datetime.now() - cached_at > timedelta(seconds=ttl):
                    cache_file.unlink()
                    count += 1
                    
            except Exception as e:
                logger.error(f"Error checking cache file {cache_file}: {e}")
        
        if count > 0:
            logger.info(f"Cleared {count} expired cache entries")
