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

# Separate client for the response cache.
# fastapi-cache stores and reads raw BYTES. The client above is created with
# decode_responses=True (returns str), and handing a str to the cache's
# decoder crashes on every cache hit — so the cache needs its own client.
_cache_redis_client: redis.Redis | None = None

def get_cache_redis_client() -> redis.Redis:
    """Get or create the bytes-mode Redis client used by fastapi-cache."""
    global _cache_redis_client
    if _cache_redis_client is None:
        _cache_redis_client = redis.from_url(settings.REDIS_URL, decode_responses=False)
    return _cache_redis_client

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """
    Dependency for FastAPI to inject a Redis client.
    """
    client = get_redis_client()
    yield client

async def close_redis():
    """Close the global Redis client."""
    global _redis_client, _cache_redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    if _cache_redis_client:
        await _cache_redis_client.close()
        _cache_redis_client = None
