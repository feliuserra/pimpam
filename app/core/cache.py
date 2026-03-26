"""Simple Redis-backed cache with graceful fallback.

All operations are fire-and-forget — if Redis is down, we just miss the cache
and queries hit the database directly.  Never blocks or raises on cache failure.
"""

import json
import logging

from app.core.redis import get_redis

logger = logging.getLogger("pimpam.cache")

PREFIX = "pimpam:cache:"


async def cache_get(key: str) -> dict | list | None:
    """Return cached value or None on miss / Redis error."""
    try:
        raw = await get_redis().get(f"{PREFIX}{key}")
        if raw is not None:
            return json.loads(raw)
    except Exception:
        logger.debug("cache_get failed for %s", key)
    return None


async def cache_set(key: str, value: dict | list, ttl: int = 300) -> None:
    """Store value with TTL (seconds). Silently ignores errors."""
    try:
        await get_redis().set(f"{PREFIX}{key}", json.dumps(value, default=str), ex=ttl)
    except Exception:
        logger.debug("cache_set failed for %s", key)


async def cache_delete(key: str) -> None:
    """Remove a single cached key."""
    try:
        await get_redis().delete(f"{PREFIX}{key}")
    except Exception:
        logger.debug("cache_delete failed for %s", key)


async def cache_delete_pattern(pattern: str) -> None:
    """Remove all keys matching a glob pattern (e.g. 'user:42*')."""
    try:
        r = get_redis()
        cursor = None
        while cursor != 0:
            cursor, keys = await r.scan(
                cursor=cursor or 0, match=f"{PREFIX}{pattern}", count=100
            )
            if keys:
                await r.delete(*keys)
    except Exception:
        logger.debug("cache_delete_pattern failed for %s", pattern)
