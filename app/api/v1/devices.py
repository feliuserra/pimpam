from fastapi import APIRouter, HTTPException, Request, status

from app.core.dependencies import CurrentUser, DBSession
from app.core.e2ee_validation import validate_spki_public_key
from app.core.limiter import limiter
from app.crud.device import (
    count_active_devices,
    create_device,
    delete_backup,
    get_backup,
    get_device_by_fingerprint,
    get_device_by_id,
    get_user_backups,
    get_user_devices,
    rename_device,
    revoke_device,
    upsert_backup,
)
from app.schemas.device import (
    BackupDownload,
    BackupUpload,
    DevicePublic,
    DeviceRegister,
    DeviceRename,
)

router = APIRouter(prefix="/devices", tags=["devices"])

MAX_ACTIVE_DEVICES = 10


@router.post("", response_model=DevicePublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def register_device(
    request: Request,
    data: DeviceRegister,
    current_user: CurrentUser,
    db: DBSession,
):
    """Register a new E2EE device. Validates the SPKI public key and stores it."""
    try:
        fingerprint = validate_spki_public_key(data.public_key)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Re-activate existing device with same fingerprint (e.g. backup restore)
    existing = await get_device_by_fingerprint(db, current_user.id, fingerprint)
    if existing:
        if existing.is_active:
            return existing
        # Reactivate revoked device with same key
        existing.is_active = True
        existing.is_revoked = False
        existing.device_name = data.device_name
        await db.commit()
        await db.refresh(existing)
        return existing

    active_count = await count_active_devices(db, current_user.id)
    if active_count >= MAX_ACTIVE_DEVICES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_ACTIVE_DEVICES} active devices allowed",
        )

    device = await create_device(
        db,
        user_id=current_user.id,
        device_name=data.device_name,
        public_key=data.public_key,
        fingerprint=fingerprint,
    )
    return device


@router.get("", response_model=list[DevicePublic])
async def list_my_devices(current_user: CurrentUser, db: DBSession):
    """List all active devices for the authenticated user."""
    return await get_user_devices(db, current_user.id)


@router.patch("/{device_id}", response_model=DevicePublic)
async def rename_my_device(
    device_id: int,
    data: DeviceRename,
    current_user: CurrentUser,
    db: DBSession,
):
    """Rename one of the authenticated user's devices."""
    device = await get_device_by_id(db, device_id)
    if device is None or device.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")
    await rename_device(db, device, data.device_name)
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/hour")
async def revoke_my_device(
    request: Request,
    device_id: int,
    current_user: CurrentUser,
    db: DBSession,
):
    """Revoke a device. It keeps its row for FK integrity but stops receiving new message keys."""
    device = await get_device_by_id(db, device_id)
    if device is None or device.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")
    if not device.is_active:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Device already revoked"
        )
    await revoke_device(db, device)


# ── Key Backup ──


@router.post(
    "/{device_id}/backup",
    status_code=status.HTTP_201_CREATED,
    response_model=BackupDownload,
)
@limiter.limit("3/hour")
async def upload_backup(
    request: Request,
    device_id: int,
    data: BackupUpload,
    current_user: CurrentUser,
    db: DBSession,
):
    """Upload an encrypted private key backup for a device."""
    device = await get_device_by_id(db, device_id)
    if device is None or device.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")

    backup = await upsert_backup(
        db,
        user_id=current_user.id,
        device_id=device_id,
        encrypted_private_key=data.encrypted_private_key,
        salt=data.salt,
        kdf=data.kdf,
        kdf_params=data.kdf_params,
    )
    return backup


@router.get("/{device_id}/backup", response_model=BackupDownload)
@limiter.limit("10/hour")
async def download_backup(
    request: Request,
    device_id: int,
    current_user: CurrentUser,
    db: DBSession,
):
    """Download the encrypted key backup for a device."""
    device = await get_device_by_id(db, device_id)
    if device is None or device.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")

    backup = await get_backup(db, current_user.id, device_id)
    if backup is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No backup found")
    return backup


@router.delete("/{device_id}/backup", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_backup(
    device_id: int,
    current_user: CurrentUser,
    db: DBSession,
):
    """Delete the encrypted key backup for a device."""
    backup = await get_backup(db, current_user.id, device_id)
    if backup is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No backup found")
    await delete_backup(db, backup)


# ── Recovery helper ──


@router.get("/backups/available", response_model=list[BackupDownload])
async def list_available_backups(current_user: CurrentUser, db: DBSession):
    """List all backups the user has. Used during recovery to check if any exist."""
    return await get_user_backups(db, current_user.id)
