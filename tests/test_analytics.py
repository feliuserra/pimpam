"""Tests for admin analytics endpoints."""

import pytest

from tests.conftest import get_test_db, setup_user


async def _make_admin(username: str):
    """Set is_admin=True directly in the DB."""
    from sqlalchemy import update

    from app.models.user import User

    async for db in get_test_db():
        await db.execute(
            update(User).where(User.username == username).values(is_admin=True)
        )
        await db.commit()


@pytest.fixture
async def admin_headers(client):
    """Register a user, promote to admin, return auth headers."""
    h = await setup_user(client, "analyticsadmin")
    await _make_admin("analyticsadmin")
    return h


@pytest.fixture
async def regular_headers(client):
    return await setup_user(client, "regularuser")


# --- Access control ---


@pytest.mark.asyncio
async def test_analytics_overview_requires_admin(client, regular_headers):
    r = await client.get("/api/v1/admin/analytics/overview", headers=regular_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_analytics_timeseries_requires_admin(client, regular_headers):
    r = await client.get(
        "/api/v1/admin/analytics/timeseries?metric=posts", headers=regular_headers
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_analytics_top_communities_requires_admin(client, regular_headers):
    r = await client.get(
        "/api/v1/admin/analytics/top-communities", headers=regular_headers
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_analytics_moderation_requires_admin(client, regular_headers):
    r = await client.get("/api/v1/admin/analytics/moderation", headers=regular_headers)
    assert r.status_code == 403


# --- Overview ---


@pytest.mark.asyncio
async def test_analytics_overview_returns_totals(client, admin_headers):
    r = await client.get("/api/v1/admin/analytics/overview", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "total_users" in data
    assert "total_posts" in data
    assert "total_comments" in data
    assert "total_communities" in data
    assert "active_users_7d" in data
    # At least the admin user exists
    assert data["total_users"] >= 1


# --- Timeseries ---


@pytest.mark.asyncio
async def test_analytics_timeseries_valid_metric(client, admin_headers):
    r = await client.get(
        "/api/v1/admin/analytics/timeseries?metric=signups&days=7",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # The admin user was just created, so there should be at least one datapoint
    if data:
        assert "date" in data[0]
        assert "count" in data[0]


@pytest.mark.asyncio
async def test_analytics_timeseries_invalid_metric_empty(client, admin_headers):
    r = await client.get(
        "/api/v1/admin/analytics/timeseries?metric=invalid",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json() == []


# --- Top communities ---


@pytest.mark.asyncio
async def test_analytics_top_communities_empty(client, admin_headers):
    r = await client.get(
        "/api/v1/admin/analytics/top-communities?days=30&limit=5",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_analytics_top_communities_with_data(client, admin_headers):
    # Create a community and a post
    await client.post(
        "/api/v1/communities",
        json={"name": "analyticscomm", "description": "For analytics"},
        headers=admin_headers,
    )
    await client.post("/api/v1/communities/analyticscomm/join", headers=admin_headers)
    comm_r = await client.get("/api/v1/communities/analyticscomm")
    community_id = comm_r.json()["id"]
    await client.post(
        "/api/v1/posts",
        json={
            "title": "Analytics post",
            "content": "Test content",
            "community_id": community_id,
        },
        headers=admin_headers,
    )
    r = await client.get(
        "/api/v1/admin/analytics/top-communities?days=30&limit=5",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert data[0]["name"] == "analyticscomm"
    assert data[0]["post_count"] >= 1


# --- Moderation summary ---


@pytest.mark.asyncio
async def test_analytics_moderation_summary(client, admin_headers):
    r = await client.get(
        "/api/v1/admin/analytics/moderation?days=30",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "pending_reports" in data
    assert "bans_count" in data
    assert "removals_count" in data
    assert "suspensions_count" in data
    # All should be zero in a fresh DB
    assert data["pending_reports"] == 0
    assert data["bans_count"] == 0


# --- UserPublic includes is_admin ---


@pytest.mark.asyncio
async def test_user_public_includes_is_admin(client, admin_headers):
    r = await client.get("/api/v1/users/me", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["is_admin"] is True


@pytest.mark.asyncio
async def test_regular_user_is_admin_false(client, regular_headers):
    r = await client.get("/api/v1/users/me", headers=regular_headers)
    assert r.status_code == 200
    assert r.json()["is_admin"] is False
