from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import ws as ws_router
from app.api.v1 import auth, communities, feed, media, messages, moderation, posts, search, users
from app.api.federation import actor_routes, wellknown
from app.core.config import settings
from app.core.limiter import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.storage_enabled:
        from app.core.storage import ensure_bucket_exists
        try:
            ensure_bucket_exists()
        except Exception:
            pass  # storage unavailable at startup — upload endpoints will return 502
    if settings.search_enabled:
        from app.core.search import configure_index
        try:
            configure_index()
        except Exception:
            pass  # search unavailable at startup — search endpoints will return 503
    from app.core.redis import get_redis
    try:
        get_redis()  # eagerly create the client; actual connection is lazy
    except Exception:
        pass
    yield
    from app.core.redis import close_redis
    await close_redis()


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

# WebSocket — no version prefix, mounted at root
app.include_router(ws_router.router)

# Federation routers — mounted at root (ActivityPub & WebFinger paths are protocol-defined)
if settings.federation_enabled:
    app.include_router(wellknown.router)
    app.include_router(actor_routes.router)


@app.get("/health", tags=["health"])
async def health():
    """Liveness probe."""
    return {"status": "ok", "version": settings.app_version, "federation": settings.federation_enabled}
