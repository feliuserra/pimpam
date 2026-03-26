from unittest.mock import patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_session
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Module-level session factory so tests can access the DB directly
_test_session_factory = None


@pytest_asyncio.fixture
async def client():
    """Each test gets a completely fresh in-memory SQLite database."""
    global _test_session_factory
    # Disable rate limiting in tests — slowapi captures key_func at decoration
    # time, so patching _key_func after the fact has no effect. Disabling is safer.
    from app.core.limiter import limiter as shared_limiter

    original_enabled = shared_limiter.enabled
    shared_limiter.enabled = False

    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    _test_session_factory = async_session

    async def override_get_session():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    # Flush any cached data from previous test runs so tests see fresh DB state
    try:
        from app.core.cache import cache_delete_pattern

        await cache_delete_pattern("*")
    except Exception:
        pass  # Redis may not be running in CI
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
    _test_session_factory = None
    shared_limiter.enabled = original_enabled
    # Reset the module-level Redis client so the next test gets a fresh one
    # bound to the correct event loop (prevents RuntimeError: Event loop is closed)
    import app.core.redis as _redis_mod

    _redis_mod._client = None
    await engine.dispose()


async def get_test_db():
    """Return an async session for direct DB access in tests."""
    if _test_session_factory is None:
        raise RuntimeError(
            "get_test_db() called outside of a test with the client fixture"
        )
    async with _test_session_factory() as session:
        yield session


# --- Helpers (plain async functions, not fixtures) ---


async def register(client, username, password="testpass123", email=None, verify=True):
    """Register a user and, by default, auto-verify their email."""
    email = email or f"{username}@example.com"
    captured = {}

    async def _capture(to, token):
        captured["token"] = token

    with patch("app.api.v1.auth.send_verification_email", new=_capture):
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
            },
        )

    if verify and "token" in captured:
        await client.get(f"/api/v1/auth/verify?token={captured['token']}")

    return r


async def login(client, username, password="testpass123"):
    r = await client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )
    return r.json()["access_token"]


async def headers(client, username, password="testpass123"):
    token = await login(client, username, password)
    return {"Authorization": f"Bearer {token}"}


async def setup_user(client, username, **kwargs):
    """Register + return auth headers."""
    await register(client, username, **kwargs)
    return await headers(client, username, kwargs.get("password", "testpass123"))
