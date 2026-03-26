"""
S3-compatible storage client.

Works with MinIO (local dev) and Cloudflare R2 (production) without code changes —
just swap environment variables. The bucket must exist and be publicly readable
before the first upload.

Bucket setup:
  MinIO:         create via console at http://localhost:9001 or `mc mb minio/pimpam`
  Cloudflare R2: create in the Cloudflare dashboard, enable public access.
"""

import io
import logging
import uuid

import boto3
from botocore.config import Config
from PIL import Image

from app.core.config import settings

logger = logging.getLogger("pimpam.storage")

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def _s3():
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint_url,
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
        region_name=settings.storage_region,
        config=Config(signature_version="s3v4"),
    )


def _process_image(data: bytes, max_px: int) -> bytes:
    """
    Open an image, resize it so the longest side is at most max_px,
    strip metadata (EXIF etc.), and re-encode as WebP.
    Raises ValueError if the data is not a valid image.
    """
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()  # catches truncated / corrupt files
        img = Image.open(
            io.BytesIO(data)
        )  # re-open after verify (verify closes the file)
    except Exception:
        raise ValueError("File is not a valid image")

    # Flatten transparency so WebP lossy works cleanly
    if img.mode in ("RGBA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Resize — thumbnail preserves aspect ratio and never upscales
    img.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="WEBP", quality=85, method=6)
    return out.getvalue()


def _is_gif(data: bytes) -> bool:
    """Check if image data is an animated GIF (or any GIF)."""
    try:
        img = Image.open(io.BytesIO(data))
        return img.format == "GIF"
    except Exception:
        return False


def _process_gif(data: bytes, max_px: int) -> bytes:
    """
    Resize an animated GIF while preserving all frames.
    Returns GIF bytes (not WebP).
    """
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
    except Exception:
        raise ValueError("File is not a valid image")

    # Calculate new size preserving aspect ratio
    w, h = img.size
    if max(w, h) <= max_px:
        # No resize needed — validate and return as-is
        return data

    scale = max_px / max(w, h)
    new_size = (int(w * scale), int(h * scale))

    frames = []
    durations = []
    try:
        while True:
            frame = img.copy().resize(new_size, Image.Resampling.LANCZOS)
            frames.append(frame)
            durations.append(img.info.get("duration", 100))
            img.seek(img.tell() + 1)
    except EOFError:
        pass

    if not frames:
        raise ValueError("File is not a valid image")

    out = io.BytesIO()
    frames[0].save(
        out,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=img.info.get("loop", 0),
        optimize=False,
    )
    return out.getvalue()


def upload_image(data: bytes, media_type: str) -> str:
    """
    Validate, process, and upload an image. Returns its public URL.

    media_type: "avatar" | "post_image" | "cover_image"
    """
    if len(data) > settings.media_max_upload_bytes:
        raise ValueError(
            f"File too large — maximum is {settings.media_max_upload_bytes // (1024 * 1024)} MB"
        )

    if media_type == "avatar":
        max_px = settings.media_avatar_max_px
    else:
        max_px = settings.media_post_image_max_px

    # Preserve GIF animation for cover images
    is_animated_gif = media_type == "cover_image" and _is_gif(data)

    if is_animated_gif:
        processed = _process_gif(data, max_px)
        ext = "gif"
        content_type = "image/gif"
    else:
        processed = _process_image(data, max_px)
        ext = "webp"
        content_type = "image/webp"

    folders = {
        "avatar": "avatars",
        "post_image": "post-images",
        "cover_image": "covers",
    }
    folder = folders.get(media_type, "uploads")
    key = f"{folder}/{uuid.uuid4()}.{ext}"

    _s3().put_object(
        Bucket=settings.storage_bucket,
        Key=key,
        Body=processed,
        ContentType=content_type,
    )

    return f"{settings.storage_public_url.rstrip('/')}/{key}"


def ensure_bucket_exists() -> None:
    """
    Create the storage bucket if it does not already exist.
    Called once at startup — safe to call repeatedly.
    """
    client = _s3()
    try:
        client.head_bucket(Bucket=settings.storage_bucket)
    except Exception:
        try:
            client.create_bucket(Bucket=settings.storage_bucket)
        except Exception:
            logger.exception(
                "Failed to create storage bucket '%s'", settings.storage_bucket
            )
