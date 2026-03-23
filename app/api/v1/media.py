"""
Media upload endpoint.

POST /api/v1/media/upload
  - Accepts a single image file (JPEG, PNG, WebP, GIF).
  - Validates file type via Pillow (not just the Content-Type header).
  - Converts to WebP and strips metadata server-side.
  - Resizes avatars to 512×512, post images to 2000px on the longest side.
  - Uploads to S3-compatible storage and returns the public URL.

The client then uses the returned URL in:
  PATCH /api/v1/users/me        → { "avatar_url": "<url>" }
  POST  /api/v1/posts           → { "image_url": "<url>", ... }

To add multiple images per post later, see docs/missing.rst.
"""
from fastapi import APIRouter, HTTPException, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.core.config import settings
from app.core.dependencies import CurrentUser
from app.core.limiter import limiter
from app.core.storage import upload_image

router = APIRouter(prefix="/media", tags=["media"])

VALID_TYPES = {"avatar", "post_image"}


class UploadResponse(BaseModel):
    url: str


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def upload(
    request: Request,
    file: UploadFile,
    media_type: str,
    current_user: CurrentUser,
):
    """
    Upload an image and receive its public URL.

    **media_type** must be ``avatar`` or ``post_image``.

    - Files are validated and converted to WebP server-side.
    - EXIF metadata (including GPS location) is stripped automatically.
    - Max file size: 10 MB.
    - Avatars are resized to 512×512 px. Post images to 2000 px on the longest side.
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

    try:
        url = await run_in_threadpool(upload_image, data, media_type)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Upload failed — storage service unavailable",
        )

    return UploadResponse(url=url)
