"""Tests for logout and change-password endpoints."""
import pytest

from tests.conftest import setup_user


async def get_refresh_token(client, username, password="testpass123"):
    r = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return r.json()["refresh_token"]


async def use_refresh_token(client, refresh_token):
    return await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

async def test_logout_returns_204(client):
    ha = await setup_user(client, "alice")
    r = await client.post("/api/v1/auth/logout", headers=ha)
    assert r.status_code == 204


async def test_logout_requires_auth(client):
    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 401


async def test_logout_invalidates_refresh_token(client):
    ha = await setup_user(client, "alice")
    refresh_token = await get_refresh_token(client, "alice")

    await client.post("/api/v1/auth/logout", headers=ha)

    r = await use_refresh_token(client, refresh_token)
    assert r.status_code == 401
    assert r.json()["detail"] == "Refresh token revoked"


async def test_logout_does_not_invalidate_access_token_mid_request(client):
    """Access tokens are stateless JWTs — they remain valid until expiry.
    This test confirms the access token in ha still works after logout
    (the short expiry window is acceptable; clients should discard it)."""
    ha = await setup_user(client, "alice")
    await client.post("/api/v1/auth/logout", headers=ha)
    # The same access token (ha) can still hit read endpoints until it expires
    r = await client.get("/api/v1/users/me", headers=ha)
    assert r.status_code == 200


async def test_login_after_logout_works(client):
    ha = await setup_user(client, "alice")
    await client.post("/api/v1/auth/logout", headers=ha)

    r = await client.post("/api/v1/auth/login", json={"username": "alice", "password": "testpass123"})
    assert r.status_code == 200
    new_refresh = r.json()["refresh_token"]

    r = await use_refresh_token(client, new_refresh)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------

async def test_change_password_success(client):
    ha = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "testpass123", "new_password": "NewPassword99!"},
        headers=ha,
    )
    assert r.status_code == 200


async def test_change_password_wrong_current_password(client):
    ha = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrongpassword", "new_password": "NewPassword99!"},
        headers=ha,
    )
    assert r.status_code == 401


async def test_change_password_requires_auth(client):
    r = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "testpass123", "new_password": "NewPassword99!"},
    )
    assert r.status_code == 401


async def test_change_password_new_password_works(client):
    ha = await setup_user(client, "alice")
    await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "testpass123", "new_password": "NewPassword99!"},
        headers=ha,
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "NewPassword99!"},
    )
    assert r.status_code == 200


async def test_change_password_old_password_rejected(client):
    ha = await setup_user(client, "alice")
    await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "testpass123", "new_password": "NewPassword99!"},
        headers=ha,
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "testpass123"},
    )
    assert r.status_code == 401


async def test_change_password_invalidates_refresh_token(client):
    ha = await setup_user(client, "alice")
    refresh_token = await get_refresh_token(client, "alice")

    await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "testpass123", "new_password": "NewPassword99!"},
        headers=ha,
    )

    r = await use_refresh_token(client, refresh_token)
    assert r.status_code == 401
    assert r.json()["detail"] == "Refresh token revoked"


async def test_change_password_new_refresh_token_works(client):
    ha = await setup_user(client, "alice")
    await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "testpass123", "new_password": "NewPassword99!"},
        headers=ha,
    )
    new_refresh = await get_refresh_token(client, "alice", password="NewPassword99!")
    r = await use_refresh_token(client, new_refresh)
    assert r.status_code == 200
