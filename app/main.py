import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import ws as ws_router
from app.api.federation import actor_routes, wellknown
from app.api.v1 import (
    auth,
    communities,
    feed,
    friend_groups,
    media,
    messages,
    moderation,
    notifications,
    posts,
    search,
    stories,
    users,
)
from app.api.v1.comments import comments_router, post_comments_router
from app.core.config import settings
from app.core.limiter import limiter

logger = logging.getLogger("pimpam.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.logging import setup_logging

    setup_logging()

    if settings.storage_enabled:
        from app.core.storage import ensure_bucket_exists

        try:
            ensure_bucket_exists()
        except Exception:
            logger.exception(
                "Storage unavailable at startup — upload endpoints will return 502"
            )
    if settings.search_enabled:
        from app.core.search import configure_index

        try:
            configure_index()
        except Exception:
            logger.exception(
                "Search unavailable at startup — search endpoints will return 503"
            )
    from app.core.redis import get_redis

    try:
        get_redis()  # eagerly create the client; actual connection is lazy
    except Exception:
        logger.exception(
            "Redis unavailable at startup — real-time features will be degraded"
        )
    cleanup_task = asyncio.create_task(_account_cleanup_loop())
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    from app.core.redis import close_redis

    await close_redis()


async def _account_cleanup_loop() -> None:
    """Hourly background task: execute due deletions, purge expired unverified accounts, and purge old consent logs."""
    from datetime import datetime as _dt
    from datetime import timedelta, timezone

    from sqlalchemy import delete

    from app.crud.account_deletion import (
        process_expired_unverified,
        process_pending_deletions,
    )
    from app.db.session import AsyncSessionLocal
    from app.models.consent import ConsentLog

    while True:
        await asyncio.sleep(3600)
        async with AsyncSessionLocal() as db:
            # Phase 1: account deletions
            try:
                await process_pending_deletions(db)
                await process_expired_unverified(db)
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception("Cleanup phase failed: account deletions")

            # Phase 2: GDPR consent log purge
            try:
                cutoff = _dt.now(timezone.utc) - timedelta(days=30)
                await db.execute(
                    delete(ConsentLog).where(ConsentLog.created_at < cutoff)
                )
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception("Cleanup phase failed: consent log purge")

            # Phase 3: expired stories
            try:
                from app.models.story import Story

                await db.execute(
                    delete(Story).where(
                        Story.expires_at < _dt.now(timezone.utc),
                        Story.is_removed == False,  # noqa: E712 — keep reported ones for mod review
                    )
                )
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception("Cleanup phase failed: expired stories")

            # Phase 4: S3 pending image deletions + quota decrement
            try:
                from sqlalchemy import select

                from app.core.storage import delete_objects
                from app.models.pending_deletion import PendingDeletion
                from app.models.user import User

                now = _dt.now(timezone.utc)
                pending = await db.execute(
                    select(PendingDeletion).where(PendingDeletion.delete_after <= now)
                )
                pending_rows = list(pending.scalars().all())
                if pending_rows:
                    s3_keys = [r.s3_key for r in pending_rows]
                    failed_keys = delete_objects(s3_keys)
                    failed_set = set(failed_keys)

                    for r in pending_rows:
                        if r.s3_key in failed_set:
                            continue  # retry next cycle
                        # Decrement user quota
                        if r.user_id and r.bytes_to_reclaim > 0:
                            user = await db.get(User, r.user_id)
                            if user:
                                user.storage_bytes_used = max(
                                    0,
                                    user.storage_bytes_used - r.bytes_to_reclaim,
                                )
                        await db.delete(r)

                    await db.commit()
            except Exception:
                await db.rollback()
                logger.exception("Cleanup phase failed: S3 pending deletions")


app = FastAPI(
    title=settings.app_name,
    description="Open-source, ad-free, human-first social network. No algorithms. No ads.",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — tighten origins in production via CORS_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache-Control headers for public, read-only GET endpoints (pure ASGI middleware)
_CC_RULES: list[tuple[str, str]] = [
    ("/api/v1/communities/", "public, max-age=30"),
    ("/api/v1/communities", "public, max-age=60"),
    ("/avatars/", "public, max-age=86400"),
]


class _CacheControlMiddleware:
    """Pure ASGI middleware — avoids BaseHTTPMiddleware async session issues."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") != "GET":
            return await self.app(scope, receive, send)

        path = scope.get("path", "")

        cc_value = None
        if "/labels" in path and path.startswith("/api/v1/communities/"):
            cc_value = "public, max-age=120"
        else:
            for prefix, cc in _CC_RULES:
                if path.startswith(prefix):
                    cc_value = cc
                    break

        if cc_value is None:
            return await self.app(scope, receive, send)

        async def send_with_cache_control(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"cache-control", cc_value.encode()))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_cache_control)


app.add_middleware(_CacheControlMiddleware)

# Routers — versioned API
_prefix = "/api/v1"
app.include_router(auth.router, prefix=_prefix)
app.include_router(users.router, prefix=_prefix)
app.include_router(feed.router, prefix=_prefix)
app.include_router(posts.router, prefix=_prefix)
app.include_router(communities.router, prefix=_prefix)
app.include_router(moderation.router, prefix=_prefix)
app.include_router(messages.router, prefix=_prefix)

from app.api.v1 import devices  # noqa: E402

app.include_router(devices.router, prefix=_prefix)
app.include_router(media.router, prefix=_prefix)
app.include_router(search.router, prefix=_prefix)
app.include_router(notifications.router, prefix=_prefix)
app.include_router(friend_groups.router, prefix=_prefix)
app.include_router(stories.router, prefix=_prefix)
app.include_router(post_comments_router, prefix=_prefix)
app.include_router(comments_router, prefix=_prefix)

from app.api.v1 import (  # noqa: E402
    admin,
    community_labels,
    curated_picks,
    hashtags,
    issues,
    reports,
)

app.include_router(community_labels.router, prefix=_prefix)
app.include_router(curated_picks.router, prefix=_prefix)
app.include_router(hashtags.router, prefix=_prefix)

app.include_router(reports.router, prefix=_prefix)
app.include_router(admin.router, prefix=_prefix)
app.include_router(issues.router, prefix=_prefix)

# WebSocket — no version prefix, mounted at root
app.include_router(ws_router.router)

# Federation routers — mounted at root (ActivityPub & WebFinger paths are protocol-defined)
if settings.federation_enabled:
    app.include_router(wellknown.router)
    app.include_router(actor_routes.router)

# Static files — default avatars
from pathlib import Path as _Path  # noqa: E402

from fastapi.staticfiles import StaticFiles as _StaticFiles  # noqa: E402

_avatars_dir = _Path(__file__).parent / "avatars"
if _avatars_dir.is_dir():
    app.mount("/avatars", _StaticFiles(directory=str(_avatars_dir)), name="avatars")


@app.get("/health", tags=["health"])
async def health():
    """Liveness probe."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "federation": settings.federation_enabled,
    }
