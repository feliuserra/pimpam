"""Resolve S3 keys to signed URLs with Redis caching.

Central module — all API endpoints call ``resolve_url`` / ``resolve_urls``
instead of exposing raw S3 keys to the frontend.

Uses the same Redis connection as ``app.core.cache`` with a dedicated prefix.
All operations are fire-and-forget: if Redis is down, signed URLs are
generated on every request (still fast — local HMAC, no network call).
"""

import logging

from app.core.config import settings
from app.core.redis import get_redis
from app.core.storage import generate_signed_url

logger = logging.getLogger("pimpam.media_urls")

_PREFIX = "pimpam:cache:signed:"
# Cache TTL is 5 minutes shorter than the signed URL TTL so cached URLs
# are always valid when served.
_CACHE_TTL = max(settings.storage_signed_url_ttl - 300, 60)


async def resolve_url(key: str | None) -> str | None:
    """Convert a single S3 key to a signed URL.

    - ``None`` / empty → ``None``
    - Starts with ``http`` → returned as-is (legacy full URLs during migration)
    - Otherwise → signed URL (cached in Redis)
    """
    if not key:
        return None
    if key.startswith("http"):
        return key

    # Try cache
    try:
        cached = await get_redis().get(f"{_PREFIX}{key}")
        if cached is not None:
            return cached.decode() if isinstance(cached, bytes) else cached
    except Exception:
        logger.debug("resolve_url cache miss for %s", key)

    signed = generate_signed_url(key)

    # Cache (fire-and-forget)
    try:
        await get_redis().set(f"{_PREFIX}{key}", signed, ex=_CACHE_TTL)
    except Exception:
        pass

    return signed


async def resolve_urls(keys: list[str | None]) -> list[str | None]:
    """Batch-resolve S3 keys to signed URLs.

    Uses a single Redis MGET for cache hits, then generates and MSET misses.
    Critical for feed endpoints with 20+ posts.
    """
    if not keys:
        return []

    results: list[str | None] = [None] * len(keys)
    # Separate indices by type
    passthrough: list[int] = []  # None / http — no work needed
    to_resolve: list[tuple[int, str]] = []  # (index, key) — need signing

    for i, key in enumerate(keys):
        if not key:
            results[i] = None
        elif key.startswith("http"):
            results[i] = key
            passthrough.append(i)
        else:
            to_resolve.append((i, key))

    if not to_resolve:
        return results

    resolve_keys = [k for _, k in to_resolve]

    # Batch cache lookup
    cached_values: list = [None] * len(resolve_keys)
    try:
        redis_keys = [f"{_PREFIX}{k}" for k in resolve_keys]
        cached_values = await get_redis().mget(*redis_keys)
    except Exception:
        logger.debug("resolve_urls MGET failed")

    # Fill from cache, collect misses
    misses: list[tuple[int, int, str]] = []  # (result_idx, resolve_idx, key)
    for j, (result_idx, key) in enumerate(to_resolve):
        cached = cached_values[j] if cached_values else None
        if cached is not None:
            val = cached.decode() if isinstance(cached, bytes) else cached
            results[result_idx] = val
        else:
            misses.append((result_idx, j, key))

    if not misses:
        return results

    # Generate signed URLs for misses
    to_cache: dict[str, str] = {}
    for result_idx, _, key in misses:
        signed = generate_signed_url(key)
        results[result_idx] = signed
        to_cache[f"{_PREFIX}{key}"] = signed

    # Batch cache set (fire-and-forget)
    if to_cache:
        try:
            pipe = get_redis().pipeline(transaction=False)
            for redis_key, signed in to_cache.items():
                pipe.set(redis_key, signed, ex=_CACHE_TTL)
            await pipe.execute()
        except Exception:
            logger.debug("resolve_urls MSET failed")

    return results


async def invalidate_url_cache(key: str) -> None:
    """Delete the cached signed URL for a key (called on image deletion)."""
    if not key or key.startswith("http"):
        return
    try:
        await get_redis().delete(f"{_PREFIX}{key}")
    except Exception:
        logger.debug("invalidate_url_cache failed for %s", key)
