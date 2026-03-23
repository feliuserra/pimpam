"""
Redis client and pub/sub helpers for WebSocket event delivery.

One channel per user: ``pimpam:user:{user_id}``
Message shape: ``{"type": "new_post"|"new_message"|"karma_update", "data": {...}}``

All publish calls are fire-and-forget — Redis being down never breaks a primary operation.
"""
import json

import redis.asyncio as aioredis

from app.core.config import settings

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return (or lazily create) the shared async Redis client."""
    global _client
    if _client is None:
        _client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def publish_to_user(user_id: int, event_type: str, data: dict) -> None:
    """
    Publish a typed event to a user's WebSocket channel.
    Silently swallows all exceptions so callers never need try/except.
    """
    try:
        payload = json.dumps({"type": event_type, "data": data})
        await get_redis().publish(f"pimpam:user:{user_id}", payload)
    except Exception:
        pass
