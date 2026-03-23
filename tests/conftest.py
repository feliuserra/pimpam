import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_session
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def client():
    """Each test gets a completely fresh in-memory SQLite database."""
    # Disable rate limiting in tests — slowapi captures key_func at decoration
    # time, so patching _key_func after the fact has no effect. Disabling is safer.
    from app.core.limiter import limiter as shared_limiter
    original_enabled = shared_limiter.enabled
    shared_limiter.enabled = False

    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    shared_limiter.enabled = original_enabled
    await engine.dispose()


# --- Helpers (plain async functions, not fixtures) ---

async def register(client, username, password="testpass123", email=None):
    email = email or f"{username}@example.com"
    return await client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
    })


async def login(client, username, password="testpass123"):
    r = await client.post("/api/v1/auth/login", json={
        "username": username,
        "password": password,
    })
    return r.json()["access_token"]


async def headers(client, username, password="testpass123"):
    token = await login(client, username, password)
    return {"Authorization": f"Bearer {token}"}


async def setup_user(client, username, **kwargs):
    """Register + return auth headers."""
    await register(client, username, **kwargs)
    return await headers(client, username, kwargs.get("password", "testpass123"))
