"""Tests for the LoginAttempt model and its CRUD helpers.

login_attempt writes use asyncio.create_task with their own AsyncSessionLocal,
which is not the test session. For these tests we exercise the CRUD functions
directly against the test session instead.
"""

import hashlib
from datetime import datetime, timedelta, timezone

import pytest

from app.crud.login_attempt import (
    _hash_ip,
    count_attempts_in_window,
    get_suspicious_ips,
    record_login_attempt,
)
from app.models.login_attempt import LoginAttempt
from tests.conftest import get_test_db, setup_user

# ---------------------------------------------------------------------------
# _hash_ip helper
# ---------------------------------------------------------------------------


def test_hash_ip_returns_sha256_hex():
    result = _hash_ip("192.168.1.1")
    expected = hashlib.sha256(b"192.168.1.1").hexdigest()
    assert result == expected
    assert len(result) == 64
    assert result != "192.168.1.1"


def test_hash_ip_none_returns_none():
    assert _hash_ip(None) is None


# ---------------------------------------------------------------------------
# record_login_attempt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_failure_stores_success_false(client):
    async for db in get_test_db():
        await record_login_attempt(db, "10.0.0.1", success=False)
        await db.commit()

    async for db in get_test_db():
        from sqlalchemy import select

        rows = (await db.execute(select(LoginAttempt))).scalars().all()
        assert len(rows) == 1
        assert rows[0].success is False
        assert rows[0].ip_hash == hashlib.sha256(b"10.0.0.1").hexdigest()


@pytest.mark.asyncio
async def test_record_success_stores_success_true(client):
    async for db in get_test_db():
        await record_login_attempt(db, "10.0.0.2", success=True)
        await db.commit()

    async for db in get_test_db():
        from sqlalchemy import select

        rows = (await db.execute(select(LoginAttempt))).scalars().all()
        assert len(rows) == 1
        assert rows[0].success is True


@pytest.mark.asyncio
async def test_record_none_ip_stores_null(client):
    async for db in get_test_db():
        await record_login_attempt(db, None, success=False)
        await db.commit()

    async for db in get_test_db():
        from sqlalchemy import select

        rows = (await db.execute(select(LoginAttempt))).scalars().all()
        assert rows[0].ip_hash is None


# ---------------------------------------------------------------------------
# count_attempts_in_window
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_count_all_attempts_in_window(client):
    async for db in get_test_db():
        await record_login_attempt(db, "1.2.3.4", success=False)
        await record_login_attempt(db, "1.2.3.4", success=True)
        await db.commit()

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    async for db in get_test_db():
        total = await count_attempts_in_window(db, cutoff)
        assert total == 2


@pytest.mark.asyncio
async def test_count_only_failures(client):
    async for db in get_test_db():
        await record_login_attempt(db, "1.2.3.4", success=False)
        await record_login_attempt(db, "1.2.3.4", success=False)
        await record_login_attempt(db, "1.2.3.4", success=True)
        await db.commit()

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    async for db in get_test_db():
        failures = await count_attempts_in_window(db, cutoff, success=False)
        assert failures == 2


@pytest.mark.asyncio
async def test_count_excludes_records_before_cutoff(client):
    async for db in get_test_db():
        # Insert an old record with a past timestamp directly
        old = LoginAttempt(
            ip_hash=_hash_ip("9.9.9.9"),
            success=False,
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        db.add(old)
        await record_login_attempt(db, "9.9.9.9", success=False)
        await db.commit()

    # Cutoff is 1 hour ago — should only count the recent attempt
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    async for db in get_test_db():
        count = await count_attempts_in_window(db, cutoff)
        assert count == 1


# ---------------------------------------------------------------------------
# get_suspicious_ips
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suspicious_ips_requires_min_failures(client):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

    async for db in get_test_db():
        # 5 failures — below min_failures=10
        for _ in range(5):
            await record_login_attempt(db, "5.5.5.5", success=False)
        await db.commit()

    async for db in get_test_db():
        result = await get_suspicious_ips(db, cutoff, min_failures=10)
        assert result == []


@pytest.mark.asyncio
async def test_suspicious_ips_returned_above_threshold(client):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

    async for db in get_test_db():
        for _ in range(12):
            await record_login_attempt(db, "6.6.6.6", success=False)
        await db.commit()

    async for db in get_test_db():
        result = await get_suspicious_ips(db, cutoff, min_failures=10)
        assert len(result) == 1
        assert result[0]["failure_count"] == 12
        assert len(result[0]["ip_hash"]) == 64


@pytest.mark.asyncio
async def test_suspicious_ips_excludes_successes(client):
    """Successful logins from an IP should not count toward its failure tally."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

    async for db in get_test_db():
        for _ in range(8):
            await record_login_attempt(db, "7.7.7.7", success=False)
        for _ in range(5):
            await record_login_attempt(db, "7.7.7.7", success=True)
        await db.commit()

    async for db in get_test_db():
        result = await get_suspicious_ips(db, cutoff, min_failures=10)
        # 8 failures < 10 threshold
        assert result == []


# ---------------------------------------------------------------------------
# Login endpoint integration (that the auth route fires the task)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failed_login_via_api_returns_401(client):
    """Sanity check: wrong password → 401. The async log task runs independently."""
    await setup_user(client, "testuser_la")
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser_la", "password": "wrongpass"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_successful_login_via_api_returns_200(client):
    """Sanity check: correct password → 200 with tokens."""
    await setup_user(client, "testuser_la2")
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser_la2", "password": "testpass123"},
    )
    assert r.status_code == 200
    assert "access_token" in r.json()
