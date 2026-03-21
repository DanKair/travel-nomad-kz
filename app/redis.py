import redis.asyncio as redis
from typing import AsyncGenerator
from app.core.config import settings

# Global redis client instance
_redis_client: redis.Redis | None = None

def get_redis_client() -> redis.Redis:
    """Get or create the global Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL, 
            encoding="utf8", 
            decode_responses=True
        )
    return _redis_client

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """
    Dependency for FastAPI to inject a Redis client.
    """
    client = get_redis_client()
    yield client

async def close_redis():
    """Close the global Redis client."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
