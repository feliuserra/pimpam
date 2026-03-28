"""Tests for the new admin security analytics endpoints."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update

from app.crud.login_attempt import record_login_attempt
from app.models.login_attempt import LoginAttempt
from app.models.user import User
from tests.conftest import get_test_db, register, setup_user


async def _make_admin(username: str):
    async for db in get_test_db():
        await db.execute(
            update(User).where(User.username == username).values(is_admin=True)
        )
        await db.commit()


async def _setup_admin(client, username="sec_admin"):
    h = await setup_user(client, username)
    await _make_admin(username)
    return h


# ---------------------------------------------------------------------------
# Auth & permissions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_security_metrics_requires_admin(client):
    h = await setup_user(client, "plain_user")
    r = await client.get("/api/v1/admin/analytics/security", headers=h)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_security_alerts_requires_admin(client):
    h = await setup_user(client, "plain_user2")
    r = await client.get("/api/v1/admin/analytics/security-alerts", headers=h)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_window_overview_requires_admin(client):
    h = await setup_user(client, "plain_user3")
    r = await client.get("/api/v1/admin/analytics/window-overview", headers=h)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_granular_timeseries_requires_admin(client):
    h = await setup_user(client, "plain_user4")
    r = await client.get("/api/v1/admin/analytics/granular-timeseries", headers=h)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Security metrics — empty state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_security_metrics_empty_window(client):
    h = await _setup_admin(client)
    r = await client.get("/api/v1/admin/analytics/security?window=1h", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["failed_logins"] == 0
    assert data["successful_logins"] == 0
    assert data["failure_rate"] == 0.0
    assert data["suspicious_ips"] == []
    assert data["window_label"] == "1h"


# ---------------------------------------------------------------------------
# Security metrics — with data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_security_metrics_counts_attempts(client):
    h = await _setup_admin(client)

    async for db in get_test_db():
        for _ in range(3):
            await record_login_attempt(db, "1.2.3.4", success=False)
        for _ in range(2):
            await record_login_attempt(db, "5.6.7.8", success=True)
        await db.commit()

    r = await client.get("/api/v1/admin/analytics/security?window=1h", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["failed_logins"] == 3
    assert data["successful_logins"] == 2
    assert data["failure_rate"] == pytest.approx(3 / 5, abs=0.001)


@pytest.mark.asyncio
async def test_security_metrics_suspicious_ips(client):
    h = await _setup_admin(client)

    async for db in get_test_db():
        for _ in range(12):
            await record_login_attempt(db, "attacker.ip", success=False)
        await db.commit()

    r = await client.get("/api/v1/admin/analytics/security?window=1h", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data["suspicious_ips"]) == 1
    assert data["suspicious_ips"][0]["failure_count"] == 12
    # IP hash must be 64-char hex (SHA-256), not the plaintext IP
    assert len(data["suspicious_ips"][0]["ip_hash"]) == 64
    assert "attacker.ip" not in data["suspicious_ips"][0]["ip_hash"]


# ---------------------------------------------------------------------------
# Security alerts — no alerts when quiet
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_security_alerts_none_when_quiet(client):
    h = await _setup_admin(client)
    r = await client.get("/api/v1/admin/analytics/security-alerts", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["alerts"] == []
    assert "generated_at" in data


# ---------------------------------------------------------------------------
# Security alerts — high_failure_rate rule
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_security_alert_high_failure_count(client):
    h = await _setup_admin(client)

    async for db in get_test_db():
        for _ in range(51):
            await record_login_attempt(db, "brute.force", success=False)
        await db.commit()

    r = await client.get("/api/v1/admin/analytics/security-alerts", headers=h)
    assert r.status_code == 200
    alerts = r.json()["alerts"]
    types = [a["alert_type"] for a in alerts]
    assert "high_failure_rate" in types

    alert = next(a for a in alerts if a["alert_type"] == "high_failure_rate")
    assert alert["value"] == 51
    assert alert["threshold"] == 50.0


# ---------------------------------------------------------------------------
# Security alerts — login_failure_ratio rule
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_security_alert_failure_ratio(client):
    h = await _setup_admin(client)

    async for db in get_test_db():
        # 7 failures + 3 successes = 70% failure rate (> 30% threshold)
        for _ in range(7):
            await record_login_attempt(db, "ratio.test", success=False)
        for _ in range(3):
            await record_login_attempt(db, "ratio.test", success=True)
        await db.commit()

    r = await client.get("/api/v1/admin/analytics/security-alerts", headers=h)
    assert r.status_code == 200
    alerts = r.json()["alerts"]
    types = [a["alert_type"] for a in alerts]
    assert "login_failure_ratio" in types

    alert = next(a for a in alerts if a["alert_type"] == "login_failure_ratio")
    assert alert["value"] == pytest.approx(0.7, abs=0.001)
    assert alert["threshold"] == 0.30


# ---------------------------------------------------------------------------
# Window overview
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_window_overview_counts_new_users(client):
    h = await _setup_admin(client)
    # Register 2 additional users
    await register(client, "newuser_a")
    await register(client, "newuser_b")

    r = await client.get("/api/v1/admin/analytics/window-overview?window=1h", headers=h)
    assert r.status_code == 200
    data = r.json()
    # At least 3 users registered in the last hour (admin + 2 new)
    assert data["new_users"] >= 3
    assert data["window_label"] == "1h"


@pytest.mark.asyncio
async def test_window_overview_all_windows_accepted(client):
    h = await _setup_admin(client)
    for window in ["1h", "24h", "7d", "30d"]:
        r = await client.get(
            f"/api/v1/admin/analytics/window-overview?window={window}", headers=h
        )
        assert r.status_code == 200, f"window={window} failed"


@pytest.mark.asyncio
async def test_window_overview_rejects_invalid_window(client):
    h = await _setup_admin(client)
    r = await client.get(
        "/api/v1/admin/analytics/window-overview?window=invalid", headers=h
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Granular timeseries (SQLite fallback path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_granular_timeseries_returns_list(client):
    h = await _setup_admin(client)
    r = await client.get(
        "/api/v1/admin/analytics/granular-timeseries?metric=signups&window=24h",
        headers=h,
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # Each point must have bucket and count
    for point in data:
        assert "bucket" in point
        assert "count" in point


@pytest.mark.asyncio
async def test_granular_timeseries_unknown_metric_returns_empty(client):
    h = await _setup_admin(client)
    r = await client.get(
        "/api/v1/admin/analytics/granular-timeseries?metric=bogus&window=24h",
        headers=h,
    )
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_granular_timeseries_all_windows(client):
    h = await _setup_admin(client)
    for window in ["1h", "24h", "7d", "30d"]:
        r = await client.get(
            f"/api/v1/admin/analytics/granular-timeseries?metric=posts&window={window}",
            headers=h,
        )
        assert r.status_code == 200, f"window={window} failed"


# ---------------------------------------------------------------------------
# LoginAttempt 30-day purge logic (unit test — no HTTP)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_attempt_purge_removes_old_records(client):
    """Records older than 30 days should be purged by the cleanup logic."""
    from sqlalchemy import delete, select

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    async for db in get_test_db():
        # Insert one old record and one recent one
        old = LoginAttempt(
            ip_hash="old_hash",
            success=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=31),
        )
        recent = LoginAttempt(
            ip_hash="new_hash",
            success=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(old)
        db.add(recent)
        await db.commit()

        # Run the same delete logic as the background loop
        await db.execute(delete(LoginAttempt).where(LoginAttempt.created_at < cutoff))
        await db.commit()

        remaining = (await db.execute(select(LoginAttempt))).scalars().all()
        assert len(remaining) == 1
        assert remaining[0].ip_hash == "new_hash"
