import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.password_reset import PasswordResetToken


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def count_recent_requests(db: AsyncSession, user_id: int) -> int:
    """Count password-reset requests for this user in the past hour."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    result = await db.execute(
        select(func.count(PasswordResetToken.id)).where(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.created_at >= cutoff,
        )
    )
    return result.scalar_one()


async def create_reset_token(db: AsyncSession, user_id: int, mode: str) -> str:
    """
    Generate a reset token, persist its hash, and return the raw token.

    mode='link'  → URL-safe random string, expires in password_reset_link_expire_minutes
    mode='code'  → 6-digit zero-padded integer, expires in password_reset_code_expire_minutes
    """
    if mode == "code":
        raw = f"{secrets.randbelow(1_000_000):06d}"
        expire_minutes = settings.password_reset_code_expire_minutes
    else:
        raw = secrets.token_urlsafe(32)
        expire_minutes = settings.password_reset_link_expire_minutes

    token = PasswordResetToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        mode=mode,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=expire_minutes),
    )
    db.add(token)
    await db.commit()
    return raw


async def consume_reset_token(db: AsyncSession, raw_token: str) -> PasswordResetToken | None:
    """
    Validate and atomically consume a reset token.

    Returns the token row on success; None if not found, already used, or expired.
    The caller is responsible for performing the actual password change.
    """
    token_hash = _hash_token(raw_token)
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    token = result.scalar_one_or_none()
    if token is None or token.used_at is not None:
        return None
    # SQLite returns naive datetimes; normalise before comparing
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    token.used_at = datetime.now(timezone.utc)
    await db.commit()
    return token
