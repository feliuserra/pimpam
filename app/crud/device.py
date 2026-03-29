from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.key_backup import KeyBackup
from app.models.user_device import UserDevice


async def count_active_devices(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(UserDevice)
        .where(UserDevice.user_id == user_id, UserDevice.is_active == True)  # noqa: E712
    )
    return result.scalar_one()


async def get_device_by_id(db: AsyncSession, device_id: int) -> UserDevice | None:
    result = await db.execute(select(UserDevice).where(UserDevice.id == device_id))
    return result.scalar_one_or_none()


async def get_device_by_fingerprint(
    db: AsyncSession, user_id: int, fingerprint: str
) -> UserDevice | None:
    result = await db.execute(
        select(UserDevice).where(
            UserDevice.user_id == user_id,
            UserDevice.public_key_fingerprint == fingerprint,
        )
    )
    return result.scalar_one_or_none()


async def create_device(
    db: AsyncSession,
    user_id: int,
    device_name: str,
    public_key: str,
    fingerprint: str,
) -> UserDevice:
    device = UserDevice(
        user_id=user_id,
        device_name=device_name,
        public_key=public_key,
        public_key_fingerprint=fingerprint,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


async def get_user_devices(db: AsyncSession, user_id: int) -> list[UserDevice]:
    result = await db.execute(
        select(UserDevice)
        .where(UserDevice.user_id == user_id, UserDevice.is_active == True)  # noqa: E712
        .order_by(UserDevice.created_at.desc())
    )
    return list(result.scalars().all())


async def get_active_device_keys_for_user(
    db: AsyncSession, user_id: int
) -> list[UserDevice]:
    """Return active devices with public_key data (for senders to encrypt)."""
    result = await db.execute(
        select(UserDevice)
        .where(UserDevice.user_id == user_id, UserDevice.is_active == True)  # noqa: E712
        .order_by(UserDevice.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_device(db: AsyncSession, device: UserDevice) -> None:
    device.is_active = False
    device.is_revoked = True
    await db.commit()


async def rename_device(db: AsyncSession, device: UserDevice, new_name: str) -> None:
    device.device_name = new_name
    await db.commit()
    await db.refresh(device)


async def touch_device(db: AsyncSession, device: UserDevice) -> None:
    """Update last_seen_at timestamp."""
    device.last_seen_at = datetime.now(timezone.utc)
    await db.commit()


# ── Key Backup ──


async def get_backup(
    db: AsyncSession, user_id: int, device_id: int
) -> KeyBackup | None:
    result = await db.execute(
        select(KeyBackup).where(
            KeyBackup.user_id == user_id, KeyBackup.device_id == device_id
        )
    )
    return result.scalar_one_or_none()


async def upsert_backup(
    db: AsyncSession,
    user_id: int,
    device_id: int,
    encrypted_private_key: str,
    salt: str,
    kdf: str,
    kdf_params: str,
) -> KeyBackup:
    existing = await get_backup(db, user_id, device_id)
    if existing:
        existing.encrypted_private_key = encrypted_private_key
        existing.salt = salt
        existing.kdf = kdf
        existing.kdf_params = kdf_params
        await db.commit()
        await db.refresh(existing)
        return existing
    backup = KeyBackup(
        user_id=user_id,
        device_id=device_id,
        encrypted_private_key=encrypted_private_key,
        salt=salt,
        kdf=kdf,
        kdf_params=kdf_params,
    )
    db.add(backup)
    await db.commit()
    await db.refresh(backup)
    return backup


async def delete_backup(db: AsyncSession, backup: KeyBackup) -> None:
    await db.delete(backup)
    await db.commit()


async def get_user_backups(db: AsyncSession, user_id: int) -> list[KeyBackup]:
    """Return all backups for a user (used during recovery to check if any exist)."""
    result = await db.execute(select(KeyBackup).where(KeyBackup.user_id == user_id))
    return list(result.scalars().all())
