import redis
from functools import lru_cache
from typing import Optional
from app.core.config import settings


@lru_cache()
def get_redis_client() -> redis.Redis:
    """
    Get Redis client configured for Redis Cloud.
    
    Returns:
        redis.Redis: Configured Redis client
    """
    redis_url = settings.get_redis_url
    
    # Parse the Redis URL to handle SSL connections properly
    if redis_url.startswith('rediss://'):
        # SSL connection for Redis Cloud
        return redis.from_url(
            redis_url,
            decode_responses=True,
            ssl_cert_reqs=None,  # Don't verify SSL certificates for Redis Cloud
            health_check_interval=30
        )
    else:
        # Regular Redis connection (local development)
        return redis.from_url(
            redis_url,
            decode_responses=True,
            health_check_interval=30
        )


def get_redis_connection() -> redis.Redis:
    """Get Redis connection for use in application."""
    return get_redis_client()


async def test_redis_connection() -> bool:
    """
    Test Redis connection.
    
    Returns:
        bool: True if connection is successful
    """
    try:
        client = get_redis_client()
        client.ping()
        return True
    except Exception as e:
        print(f"Redis connection failed: {e}")
        return False


class RedisCache:
    """Redis cache helper class."""
    
    def __init__(self):
        self.client = get_redis_client()
    
    def set(self, key: str, value: str, expiry_seconds: Optional[int] = None) -> bool:
        """Set a key-value pair in Redis."""
        try:
            return self.client.set(key, value, ex=expiry_seconds)
        except Exception as e:
            print(f"Redis SET error: {e}")
            return False
    
    def get(self, key: str) -> Optional[str]:
        """Get a value from Redis."""
        try:
            return self.client.get(key)
        except Exception as e:
            print(f"Redis GET error: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            print(f"Redis DELETE error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            print(f"Redis EXISTS error: {e}")
            return False


# Global cache instance
cache = RedisCache()
