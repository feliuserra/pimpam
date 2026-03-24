"""Tests for multi-image post support and the MULTI_IMAGE_POSTS_ENABLED flag."""
import pytest

from tests.conftest import setup_user


async def test_single_image_url_stored(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/posts", json={
        "title": "With image",
        "content": "hello",
        "image_url": "https://example.com/pic.webp",
    }, headers=h)
    assert r.status_code == 201
    data = r.json()
    assert data["image_url"] == "https://example.com/pic.webp"
    assert data["images"] == [{"url": "https://example.com/pic.webp", "display_order": 0}]


async def test_no_image_still_works(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/posts", json={
        "title": "Text only",
        "content": "no image here",
    }, headers=h)
    assert r.status_code == 201
    assert r.json()["image_url"] is None
    assert r.json()["images"] == []


async def test_multi_image_rejected_when_flag_off(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/posts", json={
        "title": "Two images",
        "content": "trying multi",
        "image_urls": ["https://example.com/a.webp", "https://example.com/b.webp"],
    }, headers=h)
    assert r.status_code == 400
    assert r.json()["detail"] == "Multiple images per post is not enabled"


async def test_single_image_via_image_urls_allowed_when_flag_off(client):
    """A single-element image_urls list is fine even when the flag is off."""
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/posts", json={
        "title": "One image via image_urls",
        "content": "ok",
        "image_urls": ["https://example.com/only.webp"],
    }, headers=h)
    assert r.status_code == 201
    data = r.json()
    assert data["image_url"] == "https://example.com/only.webp"
    assert len(data["images"]) == 1


async def test_multi_image_accepted_when_flag_on(client, monkeypatch):
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "multi_image_posts_enabled", True)

    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/posts", json={
        "title": "Gallery post",
        "content": "look at these",
        "image_urls": [
            "https://example.com/first.webp",
            "https://example.com/second.webp",
            "https://example.com/third.webp",
        ],
    }, headers=h)
    assert r.status_code == 201
    data = r.json()
    assert data["image_url"] == "https://example.com/first.webp"
    images = data["images"]
    assert len(images) == 3
    assert images[0] == {"url": "https://example.com/first.webp", "display_order": 0}
    assert images[1] == {"url": "https://example.com/second.webp", "display_order": 1}
    assert images[2] == {"url": "https://example.com/third.webp", "display_order": 2}


async def test_image_urls_takes_precedence_over_image_url(client, monkeypatch):
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "multi_image_posts_enabled", True)

    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/posts", json={
        "title": "Precedence test",
        "content": "ok",
        "image_url": "https://example.com/single.webp",
        "image_urls": ["https://example.com/multi1.webp", "https://example.com/multi2.webp"],
    }, headers=h)
    assert r.status_code == 201
    data = r.json()
    # image_urls wins; image_url should be the first of image_urls
    assert data["image_url"] == "https://example.com/multi1.webp"
    assert len(data["images"]) == 2


async def test_over_limit_rejected(client, monkeypatch):
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "multi_image_posts_enabled", True)
    monkeypatch.setattr(cfg.settings, "post_max_images", 3)

    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/posts", json={
        "title": "Too many",
        "content": "whoa",
        "image_urls": [f"https://example.com/{i}.webp" for i in range(4)],
    }, headers=h)
    assert r.status_code == 400
    assert "Maximum 3 images" in r.json()["detail"]
