from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device_token import DeviceToken


async def get_device_token(
    db: AsyncSession, user_id: int, token: str
) -> DeviceToken | None:
    result = await db.execute(
        select(DeviceToken).where(
            DeviceToken.user_id == user_id, DeviceToken.token == token
        )
    )
    return result.scalar_one_or_none()


async def register_device_token(
    db: AsyncSession, user_id: int, token: str, platform: str
) -> DeviceToken:
    """Register a device token, updating platform if the token already exists."""
    existing = await get_device_token(db, user_id, token)
    if existing:
        existing.platform = platform
        await db.commit()
        await db.refresh(existing)
        return existing
    dt = DeviceToken(user_id=user_id, token=token, platform=platform)
    db.add(dt)
    await db.commit()
    await db.refresh(dt)
    return dt


async def remove_device_token(db: AsyncSession, user_id: int, token: str) -> bool:
    """Remove a device token. Returns True if a token was deleted."""
    result = await db.execute(
        delete(DeviceToken).where(
            DeviceToken.user_id == user_id, DeviceToken.token == token
        )
    )
    await db.commit()
    return result.rowcount > 0


async def get_user_device_tokens(db: AsyncSession, user_id: int) -> list[DeviceToken]:
    result = await db.execute(
        select(DeviceToken)
        .where(DeviceToken.user_id == user_id)
        .order_by(DeviceToken.created_at.desc())
    )
    return list(result.scalars().all())
