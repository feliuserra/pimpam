"""Tests for email verification flow."""
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import setup_user


async def register(client, username):
    return await client.post("/api/v1/auth/register", json={
        "username": username,
        "email": f"{username}@example.com",
        "password": "testpass123",
    })


async def get_headers(client, username):
    r = await client.post("/api/v1/auth/login", json={"username": username, "password": "testpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

async def test_register_creates_unverified_user(client):
    with patch("app.api.v1.auth.send_verification_email", new=AsyncMock()):
        r = await register(client, "alice")
    assert r.status_code == 201
    assert r.json()["is_verified"] is False


async def test_register_sends_verification_email(client):
    captured = {}

    async def mock_send(to, token):
        captured["to"] = to
        captured["token"] = token

    with patch("app.api.v1.auth.send_verification_email", new=mock_send):
        await register(client, "alice")

    assert captured["to"] == "alice@example.com"
    assert len(captured["token"]) > 10


# ---------------------------------------------------------------------------
# Unverified access gating
# ---------------------------------------------------------------------------

async def test_unverified_user_cannot_create_post(client):
    with patch("app.api.v1.auth.send_verification_email", new=AsyncMock()):
        await register(client, "alice")
    ha = await get_headers(client, "alice")

    r = await client.post("/api/v1/posts", json={"title": "Hello", "content": "World"}, headers=ha)
    assert r.status_code == 403
    assert r.json()["detail"] == "email_not_verified"


async def test_unverified_user_can_view_own_profile(client):
    with patch("app.api.v1.auth.send_verification_email", new=AsyncMock()):
        await register(client, "alice")
    ha = await get_headers(client, "alice")

    r = await client.get("/api/v1/users/me", headers=ha)
    assert r.status_code == 200
    assert r.json()["is_verified"] is False


async def test_unverified_user_can_logout(client):
    with patch("app.api.v1.auth.send_verification_email", new=AsyncMock()):
        await register(client, "alice")
    ha = await get_headers(client, "alice")

    r = await client.post("/api/v1/auth/logout", headers=ha)
    assert r.status_code == 204


# ---------------------------------------------------------------------------
# Verify endpoint
# ---------------------------------------------------------------------------

async def test_verify_valid_token(client):
    captured = {}

    async def mock_send(to, token):
        captured["token"] = token

    with patch("app.api.v1.auth.send_verification_email", new=mock_send):
        await register(client, "alice")

    r = await client.get(f"/api/v1/auth/verify?token={captured['token']}")
    assert r.status_code == 200

    ha = await get_headers(client, "alice")
    profile = (await client.get("/api/v1/users/me", headers=ha)).json()
    assert profile["is_verified"] is True


async def test_verify_invalid_token(client):
    r = await client.get("/api/v1/auth/verify?token=not-a-real-token")
    assert r.status_code == 400


async def test_verify_token_only_works_once(client):
    captured = {}

    async def mock_send(to, token):
        captured["token"] = token

    with patch("app.api.v1.auth.send_verification_email", new=mock_send):
        await register(client, "alice")

    token = captured["token"]
    await client.get(f"/api/v1/auth/verify?token={token}")
    r = await client.get(f"/api/v1/auth/verify?token={token}")
    assert r.status_code == 400


async def test_verified_user_can_create_post(client):
    captured = {}

    async def mock_send(to, token):
        captured["token"] = token

    with patch("app.api.v1.auth.send_verification_email", new=mock_send):
        await register(client, "alice")

    await client.get(f"/api/v1/auth/verify?token={captured['token']}")
    ha = await get_headers(client, "alice")

    r = await client.post("/api/v1/posts", json={"title": "Hello", "content": "World"}, headers=ha)
    assert r.status_code == 201


# ---------------------------------------------------------------------------
# Resend verification
# ---------------------------------------------------------------------------

async def test_resend_verification(client):
    with patch("app.api.v1.auth.send_verification_email", new=AsyncMock()):
        await register(client, "alice")
    ha = await get_headers(client, "alice")

    captured = {}

    async def mock_send(to, token):
        captured["token"] = token

    with patch("app.api.v1.auth.send_verification_email", new=mock_send):
        r = await client.post("/api/v1/auth/resend-verification", headers=ha)
    assert r.status_code == 202
    assert "token" in captured


async def test_resend_new_token_works(client):
    # First token sent on registration
    first = {}
    second = {}

    async def mock_send_first(to, token):
        first["token"] = token

    async def mock_send_second(to, token):
        second["token"] = token

    with patch("app.api.v1.auth.send_verification_email", new=mock_send_first):
        await register(client, "alice")

    ha = await get_headers(client, "alice")

    with patch("app.api.v1.auth.send_verification_email", new=mock_send_second):
        await client.post("/api/v1/auth/resend-verification", headers=ha)

    # New token verifies successfully
    r = await client.get(f"/api/v1/auth/verify?token={second['token']}")
    assert r.status_code == 200


async def test_resend_returns_400_if_already_verified(client):
    captured = {}

    async def mock_send(to, token):
        captured["token"] = token

    with patch("app.api.v1.auth.send_verification_email", new=mock_send):
        await register(client, "alice")

    await client.get(f"/api/v1/auth/verify?token={captured['token']}")
    ha = await get_headers(client, "alice")

    r = await client.post("/api/v1/auth/resend-verification", headers=ha)
    assert r.status_code == 400
