"""
Integration tests for AC-10 GDPR compliance endpoints.

Covers data export, consent log, and DELETE /users/me alias.
"""
import pytest

from tests.conftest import register, setup_user


# ---------------------------------------------------------------------------
# Data export
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_data_export_returns_all_top_level_fields(client):
    hdrs = await setup_user(client, "alice")
    r = await client.get("/api/v1/users/me/data-export", headers=hdrs)
    assert r.status_code == 200
    data = r.json()
    for key in ("exported_at", "profile", "posts", "comments", "messages_sent",
                "messages_received", "following", "followers", "community_karma", "consent_log"):
        assert key in data, f"missing key: {key}"


@pytest.mark.asyncio
async def test_data_export_profile_fields(client):
    hdrs = await setup_user(client, "alice")
    r = await client.get("/api/v1/users/me/data-export", headers=hdrs)
    profile = r.json()["profile"]
    for key in ("id", "username", "email", "karma", "created_at"):
        assert key in profile


@pytest.mark.asyncio
async def test_data_export_includes_posts(client):
    hdrs = await setup_user(client, "alice")
    await client.post("/api/v1/posts", json={"title": "Hello", "content": "World"}, headers=hdrs)

    r = await client.get("/api/v1/users/me/data-export", headers=hdrs)
    titles = [p["title"] for p in r.json()["posts"]]
    assert "Hello" in titles


@pytest.mark.asyncio
async def test_data_export_excludes_removed_posts(client):
    hdrs = await setup_user(client, "alice")
    rp = await client.post("/api/v1/posts", json={"title": "Gone", "content": "bye"}, headers=hdrs)
    post_id = rp.json()["id"]
    await client.delete(f"/api/v1/posts/{post_id}", headers=hdrs)

    r = await client.get("/api/v1/users/me/data-export", headers=hdrs)
    titles = [p["title"] for p in r.json()["posts"]]
    assert "Gone" not in titles


@pytest.mark.asyncio
async def test_data_export_requires_auth(client):
    r = await client.get("/api/v1/users/me/data-export")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Consent log
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consent_logged_on_register(client):
    hdrs = await setup_user(client, "alice")
    r = await client.get("/api/v1/users/me/data-export", headers=hdrs)
    consent_log = r.json()["consent_log"]
    assert len(consent_log) == 3
    types = {entry["consent_type"] for entry in consent_log}
    assert types == {"terms_of_service", "privacy_policy", "age_confirmation"}


@pytest.mark.asyncio
async def test_consent_log_has_version(client):
    hdrs = await setup_user(client, "alice")
    r = await client.get("/api/v1/users/me/data-export", headers=hdrs)
    for entry in r.json()["consent_log"]:
        assert entry["version"] == "1.0"
        assert entry["created_at"] is not None


# ---------------------------------------------------------------------------
# DELETE /users/me (alias for POST /users/me/delete)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_me_schedules_deletion(client):
    hdrs = await setup_user(client, "alice")
    r = await client.request(
        "DELETE", "/api/v1/users/me",
        json={"password": "testpass123"},
        headers=hdrs,
    )
    assert r.status_code == 202
    assert "deletion" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_me_wrong_password(client):
    hdrs = await setup_user(client, "alice")
    r = await client.request(
        "DELETE", "/api/v1/users/me",
        json={"password": "wrongpassword"},
        headers=hdrs,
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_delete_me_already_scheduled(client):
    hdrs = await setup_user(client, "alice")
    # Schedule once via POST
    await client.post("/api/v1/users/me/delete", json={"password": "testpass123"}, headers=hdrs)
    # Second attempt via DELETE should 409
    r = await client.request(
        "DELETE", "/api/v1/users/me",
        json={"password": "testpass123"},
        headers=hdrs,
    )
    assert r.status_code == 409
