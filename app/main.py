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
        try:
            async with AsyncSessionLocal() as db:
                await process_pending_deletions(db)
                await process_expired_unverified(db)
                # GDPR: purge consent log entries older than 30 days
                cutoff = _dt.now(timezone.utc) - timedelta(days=30)
                await db.execute(
                    delete(ConsentLog).where(ConsentLog.created_at < cutoff)
                )
                # Stories: hard-delete expired non-reported stories
                from app.models.story import Story

                await db.execute(
                    delete(Story).where(
                        Story.expires_at < _dt.now(timezone.utc),
                        Story.is_removed == False,  # noqa: E712 — keep reported ones for mod review
                    )
                )
                await db.commit()
        except Exception:
            logger.exception("Account cleanup loop failed")


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

# Routers — versioned API
_prefix = "/api/v1"
app.include_router(auth.router, prefix=_prefix)
app.include_router(users.router, prefix=_prefix)
app.include_router(feed.router, prefix=_prefix)
app.include_router(posts.router, prefix=_prefix)
app.include_router(communities.router, prefix=_prefix)
app.include_router(moderation.router, prefix=_prefix)
app.include_router(messages.router, prefix=_prefix)
app.include_router(media.router, prefix=_prefix)
app.include_router(search.router, prefix=_prefix)
app.include_router(notifications.router, prefix=_prefix)
app.include_router(friend_groups.router, prefix=_prefix)
app.include_router(stories.router, prefix=_prefix)
app.include_router(post_comments_router, prefix=_prefix)
app.include_router(comments_router, prefix=_prefix)

from app.api.v1 import admin, reports  # noqa: E402

app.include_router(reports.router, prefix=_prefix)
app.include_router(admin.router, prefix=_prefix)

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
