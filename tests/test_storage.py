"""
Tests for app/core/storage.py — image processing and S3 upload.
"""
import io
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.core import storage as storage_mod
from app.core.storage import _process_image, upload_image, ensure_bucket_exists


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_image(mode: str = "RGB", size: tuple = (200, 200)) -> bytes:
    """Return raw bytes for a minimal image in the given mode."""
    img = Image.new(mode, size, color=(100, 150, 200) if mode == "RGB" else (100, 150, 200, 255))
    buf = io.BytesIO()
    fmt = "PNG" if mode in ("RGBA", "P") else "JPEG"
    img.save(buf, format=fmt)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# _process_image
# ---------------------------------------------------------------------------

def test_process_image_rgb_returns_webp():
    data = _make_image("RGB")
    result = _process_image(data, max_px=128)
    # WebP magic bytes: RIFF????WEBP
    assert result[:4] == b"RIFF"
    assert result[8:12] == b"WEBP"


def test_process_image_respects_max_px():
    """Image wider than max_px is scaled down."""
    data = _make_image("RGB", size=(800, 600))
    result = _process_image(data, max_px=100)
    out_img = Image.open(io.BytesIO(result))
    assert max(out_img.size) <= 100


def test_process_image_does_not_upscale():
    """Small image is not upscaled past its original size."""
    data = _make_image("RGB", size=(50, 50))
    result = _process_image(data, max_px=500)
    out_img = Image.open(io.BytesIO(result))
    assert max(out_img.size) <= 50


def test_process_image_rgba_flattened_to_rgb():
    """RGBA image transparency is composited and result is WebP."""
    data = _make_image("RGBA")
    result = _process_image(data, max_px=256)
    out_img = Image.open(io.BytesIO(result))
    assert out_img.mode == "RGB"


def test_process_image_palette_mode():
    """Palette (P) image is converted without error."""
    img = Image.new("P", (100, 100))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = _process_image(buf.getvalue(), max_px=256)
    assert result[:4] == b"RIFF"


def test_process_image_invalid_data_raises():
    with pytest.raises(ValueError, match="valid image"):
        _process_image(b"not an image at all", max_px=256)


def test_process_image_truncated_data_raises():
    """Partially valid image bytes trigger the verify() failure."""
    data = _make_image("RGB")
    with pytest.raises(ValueError, match="valid image"):
        _process_image(data[:50], max_px=256)


# ---------------------------------------------------------------------------
# upload_image
# ---------------------------------------------------------------------------

def _mock_s3():
    m = MagicMock()
    m.put_object = MagicMock()
    return m


def test_upload_image_too_large_raises():
    big = b"x" * (storage_mod.settings.media_max_upload_bytes + 1)
    with pytest.raises(ValueError, match="too large"):
        upload_image(big, "avatar")


def test_upload_image_avatar_uses_avatar_folder():
    s3 = _mock_s3()
    with (
        patch("app.core.storage._s3", return_value=s3),
        patch.object(storage_mod.settings, "storage_bucket", "pimpam-test"),
        patch.object(storage_mod.settings, "storage_public_url", "https://cdn.example.com"),
    ):
        url = upload_image(_make_image("RGB"), "avatar")

    assert "avatars/" in url
    assert url.startswith("https://cdn.example.com/")
    s3.put_object.assert_called_once()
    call_kwargs = s3.put_object.call_args.kwargs
    assert call_kwargs["ContentType"] == "image/webp"
    assert call_kwargs["Key"].startswith("avatars/")


def test_upload_image_post_image_uses_post_images_folder():
    s3 = _mock_s3()
    with (
        patch("app.core.storage._s3", return_value=s3),
        patch.object(storage_mod.settings, "storage_bucket", "pimpam-test"),
        patch.object(storage_mod.settings, "storage_public_url", "https://cdn.example.com"),
    ):
        url = upload_image(_make_image("RGB"), "post_image")

    assert "post-images/" in url
    call_kwargs = s3.put_object.call_args.kwargs
    assert call_kwargs["Key"].startswith("post-images/")


def test_upload_image_url_has_unique_key():
    """Two calls produce different keys (uuid4)."""
    s3a, s3b = _mock_s3(), _mock_s3()
    data = _make_image("RGB")
    with (
        patch.object(storage_mod.settings, "storage_bucket", "pimpam-test"),
        patch.object(storage_mod.settings, "storage_public_url", "https://cdn.example.com"),
    ):
        with patch("app.core.storage._s3", return_value=s3a):
            url1 = upload_image(data, "avatar")
        with patch("app.core.storage._s3", return_value=s3b):
            url2 = upload_image(data, "avatar")

    assert url1 != url2


# ---------------------------------------------------------------------------
# ensure_bucket_exists
# ---------------------------------------------------------------------------

def test_ensure_bucket_exists_when_bucket_already_exists():
    """head_bucket succeeds → create_bucket is never called."""
    s3 = _mock_s3()
    s3.head_bucket = MagicMock(return_value={})
    with patch("app.core.storage._s3", return_value=s3):
        ensure_bucket_exists()
    s3.head_bucket.assert_called_once()
    s3.create_bucket.assert_not_called()


def test_ensure_bucket_exists_creates_when_missing():
    """head_bucket raises → create_bucket is called."""
    s3 = _mock_s3()
    s3.head_bucket = MagicMock(side_effect=Exception("NoSuchBucket"))
    s3.create_bucket = MagicMock()
    with patch("app.core.storage._s3", return_value=s3):
        ensure_bucket_exists()
    s3.create_bucket.assert_called_once()


def test_ensure_bucket_exists_swallows_create_error():
    """If create_bucket also fails (race condition), the error is swallowed."""
    s3 = _mock_s3()
    s3.head_bucket = MagicMock(side_effect=Exception("NoSuchBucket"))
    s3.create_bucket = MagicMock(side_effect=Exception("BucketAlreadyExists"))
    with patch("app.core.storage._s3", return_value=s3):
        ensure_bucket_exists()  # must not raise
