"""
Media upload endpoint.

POST /api/v1/media/upload
  - Accepts a single image file (JPEG, PNG, WebP, GIF).
  - Validates file type via Pillow (not just the Content-Type header).
  - Converts to WebP (quality 78) and strips metadata server-side.
  - Generates multiple size variants (thumb, medium, full).
  - Uploads to S3-compatible storage with SSE-S3 encryption.
  - Enforces per-user storage quotas (500 MB default).
  - Returns both a signed URL (for immediate preview) and an S3 key (for DB storage).
"""

from fastapi import APIRouter, HTTPException, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.core.config import settings
from app.core.dependencies import CurrentUser, DBSession
from app.core.limiter import limiter
from app.core.storage import generate_signed_url, upload_image_v2

router = APIRouter(prefix="/media", tags=["media"])

VALID_TYPES = {"avatar", "post_image", "cover_image"}


class UploadResponse(BaseModel):
    url: str  # signed URL of the full variant (for immediate preview)
    key: str  # S3 base key (store in DB)


@router.post(
    "/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("10/minute")
async def upload(
    request: Request,
    file: UploadFile,
    media_type: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Upload an image and receive a signed URL + S3 key.

    **media_type** must be ``avatar``, ``post_image``, or ``cover_image``.

    - Files are validated and converted to WebP server-side.
    - EXIF metadata (including GPS location) is stripped automatically.
    - Multiple size variants are generated (thumb, medium, full).
    - All uploads are encrypted at rest (SSE-S3).
    - Max file size: 10 MB.
    - Per-user storage quota: 500 MB.
    """
    if not settings.storage_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media uploads are not configured on this server",
        )

    if media_type not in VALID_TYPES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"media_type must be one of: {', '.join(VALID_TYPES)}",
        )

    data = await file.read()

    # Quota check (estimate = raw upload size; actual will be smaller after compression)
    remaining = settings.storage_user_quota_bytes - current_user.storage_bytes_used
    if len(data) > remaining:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Storage quota exceeded",
        )

    try:
        result = await run_in_threadpool(
            upload_image_v2, data, media_type, current_user.id
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Upload failed — storage service unavailable",
        )

    # Update user's storage quota
    current_user.storage_bytes_used += result["total_bytes"]
    await db.commit()

    # Generate signed URL for the full variant (immediate preview)
    full_key = result["keys"].get("full") or list(result["keys"].values())[0]
    signed_url = generate_signed_url(full_key)

    return UploadResponse(url=signed_url, key=result["key"])
