"""
Redis Client Configuration
"""
import redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Create Redis connection
redis_client = None


def get_redis():
    """Get Redis client instance"""
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    return redis_client


def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        redis_client.close()
        redis_client = None
        logger.info("Redis connection closed")

