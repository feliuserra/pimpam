from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1 import auth, communities, feed, messages, moderation, posts, users
from app.api.federation import actor_routes, wellknown
from app.core.config import settings

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Add startup logic here (e.g. cache warm-up, health checks)
    yield
    # Add shutdown logic here (e.g. close connections)


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

# Federation routers — mounted at root (ActivityPub & WebFinger paths are protocol-defined)
if settings.federation_enabled:
    app.include_router(wellknown.router)
    app.include_router(actor_routes.router)


@app.get("/health", tags=["health"])
async def health():
    """Liveness probe."""
    return {"status": "ok", "version": settings.app_version, "federation": settings.federation_enabled}
