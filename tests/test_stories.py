"""
Integration tests for ephemeral stories (POST/GET /stories, DELETE, report).
Also covers the unified feed (followed users + joined communities).
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from tests.conftest import get_test_db, setup_user
from app.models.story import Story


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_story(client, headers, image_url="https://cdn.example.com/img.webp", caption=None, duration_hours=24):
    r = await client.post("/api/v1/stories", headers=headers, json={
        "image_url": image_url,
        "caption": caption,
        "duration_hours": duration_hours,
    })
    return r


# ---------------------------------------------------------------------------
# Create story
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_story_returns_201(client):
    hdrs = await setup_user(client, "alice")
    r = await _make_story(client, hdrs, caption="Hello world")
    assert r.status_code == 201
    body = r.json()
    assert body["author_username"] == "alice"
    assert body["caption"] == "Hello world"
    assert body["image_url"] == "https://cdn.example.com/img.webp"
    assert "expires_at" not in body  # must not leak expiry


@pytest.mark.asyncio
async def test_create_story_requires_auth(client):
    r = await client.post("/api/v1/stories", json={"image_url": "https://cdn.example.com/x.webp"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_create_story_caption_optional(client):
    hdrs = await setup_user(client, "alice")
    r = await _make_story(client, hdrs)
    assert r.status_code == 201
    assert r.json()["caption"] is None


@pytest.mark.asyncio
async def test_create_story_invalid_duration_falls_back_to_24h(client):
    hdrs = await setup_user(client, "alice")
    r = await client.post("/api/v1/stories", headers=hdrs, json={
        "image_url": "https://cdn.example.com/x.webp",
        "duration_hours": 999,  # not in allowed set
    })
    assert r.status_code == 201
    story_id = r.json()["id"]
    # Verify expires_at is ~24h from now (SQLite returns naive datetimes)
    async for session in get_test_db():
        result = await session.execute(select(Story).where(Story.id == story_id))
        story = result.scalar_one()
        expires = story.expires_at.replace(tzinfo=None) if story.expires_at.tzinfo else story.expires_at
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        delta = expires - now
        assert 23 <= delta.total_seconds() / 3600 <= 25


@pytest.mark.asyncio
async def test_create_story_custom_duration(client):
    hdrs = await setup_user(client, "alice")
    r = await client.post("/api/v1/stories", headers=hdrs, json={
        "image_url": "https://cdn.example.com/x.webp",
        "duration_hours": 168,  # 7 days
    })
    assert r.status_code == 201
    story_id = r.json()["id"]
    async for session in get_test_db():
        result = await session.execute(select(Story).where(Story.id == story_id))
        story = result.scalar_one()
        expires = story.expires_at.replace(tzinfo=None) if story.expires_at.tzinfo else story.expires_at
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        delta = expires - now
        assert 167 <= delta.total_seconds() / 3600 <= 169


# ---------------------------------------------------------------------------
# Stories feed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stories_feed_includes_followed_users(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await client.post("/api/v1/users/alice/follow", headers=bob_h)
    await _make_story(client, alice_h)

    r = await client.get("/api/v1/stories/feed", headers=bob_h)
    assert r.status_code == 200
    stories = r.json()
    assert any(s["author_username"] == "alice" for s in stories)


@pytest.mark.asyncio
async def test_stories_feed_excludes_own_stories(client):
    alice_h = await setup_user(client, "alice")
    await _make_story(client, alice_h)

    r = await client.get("/api/v1/stories/feed", headers=alice_h)
    assert r.status_code == 200
    assert all(s["author_username"] != "alice" for s in r.json())


@pytest.mark.asyncio
async def test_stories_feed_excludes_reported_stories(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await client.post("/api/v1/users/alice/follow", headers=bob_h)
    story_r = await _make_story(client, alice_h)
    story_id = story_r.json()["id"]

    # bob reports the story
    await client.post(f"/api/v1/stories/{story_id}/report", headers=bob_h)

    r = await client.get("/api/v1/stories/feed", headers=bob_h)
    assert all(s["id"] != story_id for s in r.json())


@pytest.mark.asyncio
async def test_stories_feed_includes_community_member_stories(client):
    """Stories from members of joined communities appear in the feed."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    # alice creates a community, bob joins
    await client.post("/api/v1/communities", headers=alice_h, json={"name": "general", "description": "Test"})
    await client.post("/api/v1/communities/general/join", headers=bob_h)

    # alice posts a story (alice is a community member)
    await _make_story(client, alice_h)

    # bob is NOT following alice, but they share a community
    r = await client.get("/api/v1/stories/feed", headers=bob_h)
    assert r.status_code == 200
    assert any(s["author_username"] == "alice" for s in r.json())


@pytest.mark.asyncio
async def test_stories_feed_no_expiry_in_response(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await client.post("/api/v1/users/alice/follow", headers=bob_h)
    await _make_story(client, alice_h)

    r = await client.get("/api/v1/stories/feed", headers=bob_h)
    for story in r.json():
        assert "expires_at" not in story


# ---------------------------------------------------------------------------
# Delete story
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_own_story(client):
    alice_h = await setup_user(client, "alice")
    story_id = (await _make_story(client, alice_h)).json()["id"]

    r = await client.delete(f"/api/v1/stories/{story_id}", headers=alice_h)
    assert r.status_code == 204

    async for session in get_test_db():
        result = await session.execute(select(Story).where(Story.id == story_id))
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_other_users_story_is_403(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    story_id = (await _make_story(client, alice_h)).json()["id"]

    r = await client.delete(f"/api/v1/stories/{story_id}", headers=bob_h)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_delete_nonexistent_story_is_404(client):
    alice_h = await setup_user(client, "alice")
    r = await client.delete("/api/v1/stories/9999", headers=alice_h)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Report story
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_report_story_soft_deletes(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    story_id = (await _make_story(client, alice_h)).json()["id"]

    r = await client.post(f"/api/v1/stories/{story_id}/report", headers=bob_h)
    assert r.status_code == 204

    async for session in get_test_db():
        result = await session.execute(select(Story).where(Story.id == story_id))
        story = result.scalar_one_or_none()
        assert story is not None  # row still exists (retained for mod review)
        assert story.is_removed is True


@pytest.mark.asyncio
async def test_report_already_removed_story_is_404(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    carol_h = await setup_user(client, "carol")
    story_id = (await _make_story(client, alice_h)).json()["id"]

    await client.post(f"/api/v1/stories/{story_id}/report", headers=bob_h)
    r = await client.post(f"/api/v1/stories/{story_id}/report", headers=carol_h)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Unified feed (followed users + joined communities)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feed_includes_joined_community_posts(client):
    """Posts in joined communities appear in the feed even without following the author."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    await client.post("/api/v1/communities", headers=alice_h, json={"name": "tech", "description": "Tech"})
    await client.post("/api/v1/communities/tech/join", headers=bob_h)

    comm_r = await client.get("/api/v1/communities/tech")
    comm_id = comm_r.json()["id"]

    await client.post("/api/v1/posts", headers=alice_h, json={
        "title": "Community post", "content": "hello", "community_id": comm_id
    })

    r = await client.get("/api/v1/feed", headers=bob_h)
    assert r.status_code == 200
    titles = [p["title"] for p in r.json()]
    assert "Community post" in titles


@pytest.mark.asyncio
async def test_feed_deduplicates_followed_author_in_joined_community(client):
    """A post from a followed user in a joined community appears only once."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    await client.post("/api/v1/communities", headers=alice_h, json={"name": "tech", "description": "Tech"})
    await client.post("/api/v1/communities/tech/join", headers=bob_h)
    await client.post("/api/v1/users/alice/follow", headers=bob_h)

    comm_r = await client.get("/api/v1/communities/tech")
    comm_id = comm_r.json()["id"]

    await client.post("/api/v1/posts", headers=alice_h, json={
        "title": "Dedup test", "content": "x", "community_id": comm_id
    })

    r = await client.get("/api/v1/feed", headers=bob_h)
    titles = [p["title"] for p in r.json()]
    assert titles.count("Dedup test") == 1


@pytest.mark.asyncio
async def test_feed_excludes_unjoined_community_posts(client):
    """Posts in communities the viewer hasn't joined do not appear."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    await client.post("/api/v1/communities", headers=alice_h, json={"name": "secret", "description": "S"})
    comm_r = await client.get("/api/v1/communities/secret")
    comm_id = comm_r.json()["id"]

    await client.post("/api/v1/posts", headers=alice_h, json={
        "title": "Not for bob", "content": "x", "community_id": comm_id
    })

    r = await client.get("/api/v1/feed", headers=bob_h)
    titles = [p["title"] for p in r.json()]
    assert "Not for bob" not in titles
