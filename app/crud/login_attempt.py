"""CRUD helpers for the login_attempts table.

Write side: record_login_attempt — called fire-and-forget from auth.py.
Read side: count_attempts_in_window, get_suspicious_ips — called by analytics.
"""

import hashlib
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.login_attempt import LoginAttempt


def _hash_ip(ip: str | None) -> str | None:
    """SHA-256 hex digest of an IP address. Returns None if ip is None."""
    if ip is None:
        return None
    return hashlib.sha256(ip.encode()).hexdigest()


async def record_login_attempt(db: AsyncSession, ip: str | None, success: bool) -> None:
    """Persist a single login attempt row. The caller must commit the session."""
    attempt = LoginAttempt(
        ip_hash=_hash_ip(ip),
        success=success,
    )
    db.add(attempt)


async def count_attempts_in_window(
    db: AsyncSession,
    cutoff: datetime,
    success: bool | None = None,
) -> int:
    """Count login attempts since *cutoff*. Filter by success/failure when provided."""
    stmt = (
        select(func.count())
        .select_from(LoginAttempt)
        .where(LoginAttempt.created_at >= cutoff)
    )
    if success is not None:
        stmt = stmt.where(LoginAttempt.success == success)
    return (await db.execute(stmt)).scalar() or 0


async def get_suspicious_ips(
    db: AsyncSession,
    cutoff: datetime,
    min_failures: int = 10,
) -> list[dict]:
    """Return ip_hash values with >= min_failures failures since *cutoff*, descending."""
    stmt = (
        select(LoginAttempt.ip_hash, func.count().label("failure_count"))
        .where(
            LoginAttempt.created_at >= cutoff,
            LoginAttempt.success == False,  # noqa: E712
            LoginAttempt.ip_hash.is_not(None),
        )
        .group_by(LoginAttempt.ip_hash)
        .having(func.count() >= min_failures)
        .order_by(func.count().desc())
        .limit(20)
    )
    rows = (await db.execute(stmt)).all()
    return [{"ip_hash": r.ip_hash, "failure_count": r.failure_count} for r in rows]
