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
    img.save(out, format="WEBP", quality=78, method=6)
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


# ---------------------------------------------------------------------------
# v2 — multi-size, signed URLs, SSE-S3, user-scoped keys
# ---------------------------------------------------------------------------

_SIZE_CONFIGS = {
    "avatar": [("full", settings.media_avatar_max_px)],
    "post_image": [
        ("thumb", settings.media_thumb_max_px),
        ("medium", settings.media_medium_max_px),
        ("full", settings.media_post_image_max_px),
    ],
    "cover_image": [
        ("thumb", settings.media_thumb_max_px),
        ("medium", settings.media_medium_max_px),
        ("full", settings.media_post_image_max_px),
    ],
}

_FOLDER_MAP = {
    "avatar": "avatars",
    "post_image": "post-images",
    "cover_image": "covers",
}


def _process_image_sizes(
    data: bytes, media_type: str
) -> dict[str, tuple[bytes, str, str]]:
    """Process image into multiple sizes.

    Returns ``{size_label: (bytes, extension, content_type)}``.

    Animated GIFs (cover_image only) produce a single ``"full"`` variant to
    preserve animation.
    """
    is_animated_gif = media_type == "cover_image" and _is_gif(data)

    if is_animated_gif:
        max_px = settings.media_post_image_max_px
        processed = _process_gif(data, max_px)
        return {"full": (processed, "gif", "image/gif")}

    sizes = _SIZE_CONFIGS.get(media_type, _SIZE_CONFIGS["post_image"])
    result: dict[str, tuple[bytes, str, str]] = {}
    for label, max_px in sizes:
        processed = _process_image(data, max_px)
        result[label] = (processed, "webp", "image/webp")
    return result


def upload_image_v2(data: bytes, media_type: str, user_id: int) -> dict:
    """Validate, process, and upload an image with multi-size variants.

    Returns::

        {
            "key": "users/42/post-images/abc123",          # base key (store in DB)
            "keys": {"thumb": "...webp", "medium": "...", "full": "..."},
            "total_bytes": 123456,
        }

    All uploads use SSE-S3 encryption (``AES256``).
    """
    if len(data) > settings.media_max_upload_bytes:
        raise ValueError(
            f"File too large — maximum is "
            f"{settings.media_max_upload_bytes // (1024 * 1024)} MB"
        )

    variants = _process_image_sizes(data, media_type)
    folder = _FOLDER_MAP.get(media_type, "uploads")
    base_id = uuid.uuid4()
    base_key = f"users/{user_id}/{folder}/{base_id}"

    client = _s3()
    keys: dict[str, str] = {}
    total_bytes = 0

    for label, (blob, ext, content_type) in variants.items():
        if media_type == "avatar" and label == "full":
            # Avatars are single-size — no suffix
            key = f"{base_key}.{ext}"
        else:
            key = f"{base_key}_{label}.{ext}"

        put_kwargs = {
            "Bucket": settings.storage_bucket,
            "Key": key,
            "Body": blob,
            "ContentType": content_type,
        }
        if settings.environment != "development":
            put_kwargs["ServerSideEncryption"] = "AES256"
        client.put_object(**put_kwargs)
        keys[label] = key
        total_bytes += len(blob)

    return {
        "key": base_key,
        "keys": keys,
        "total_bytes": total_bytes,
    }


def generate_signed_url(key: str, expires_in: int | None = None) -> str:
    """Generate a pre-signed GET URL for an S3 object.

    This is a local HMAC computation — no network call to S3.
    """
    if expires_in is None:
        expires_in = settings.storage_signed_url_ttl

    return _s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.storage_bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def delete_objects(keys: list[str]) -> list[str]:
    """Batch-delete S3 objects. Returns list of keys that failed to delete."""
    if not keys:
        return []

    objects = [{"Key": k} for k in keys]
    try:
        resp = _s3().delete_objects(
            Bucket=settings.storage_bucket,
            Delete={"Objects": objects, "Quiet": False},
        )
        errors = resp.get("Errors", [])
        if errors:
            failed = [e["Key"] for e in errors]
            logger.warning(
                "Failed to delete %d/%d S3 objects: %s",
                len(failed),
                len(keys),
                failed,
            )
            return failed
        return []
    except Exception:
        logger.exception("Failed to delete %d S3 objects", len(keys))
        return list(keys)


def get_object_size(key: str) -> int:
    """Return the size in bytes of an S3 object, or 0 on error."""
    try:
        resp = _s3().head_object(Bucket=settings.storage_bucket, Key=key)
        return resp.get("ContentLength", 0)
    except Exception:
        logger.debug("head_object failed for %s", key)
        return 0
