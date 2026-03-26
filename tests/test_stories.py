"""
Integration tests for ephemeral stories (POST/GET /stories, DELETE, report).
Also covers the unified feed (followed users + joined communities),
link stories, and @mention tagging.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.story import Story
from app.models.story_mention import StoryMention
from tests.conftest import get_test_db, setup_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_story(
    client,
    headers,
    image_url="https://cdn.example.com/img.webp",
    caption=None,
    duration_hours=24,
    link_url=None,
):
    payload = {"duration_hours": duration_hours}
    if image_url:
        payload["image_url"] = image_url
    if caption:
        payload["caption"] = caption
    if link_url:
        payload["link_url"] = link_url
    r = await client.post("/api/v1/stories", headers=headers, json=payload)
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
    r = await client.post(
        "/api/v1/stories", json={"image_url": "https://cdn.example.com/x.webp"}
    )
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
    r = await client.post(
        "/api/v1/stories",
        headers=hdrs,
        json={
            "image_url": "https://cdn.example.com/x.webp",
            "duration_hours": 999,  # not in allowed set
        },
    )
    assert r.status_code == 201
    story_id = r.json()["id"]
    # Verify expires_at is ~24h from now (SQLite returns naive datetimes)
    async for session in get_test_db():
        result = await session.execute(select(Story).where(Story.id == story_id))
        story = result.scalar_one()
        expires = (
            story.expires_at.replace(tzinfo=None)
            if story.expires_at.tzinfo
            else story.expires_at
        )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        delta = expires - now
        assert 23 <= delta.total_seconds() / 3600 <= 25


@pytest.mark.asyncio
async def test_create_story_custom_duration(client):
    hdrs = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/stories",
        headers=hdrs,
        json={
            "image_url": "https://cdn.example.com/x.webp",
            "duration_hours": 168,  # 7 days
        },
    )
    assert r.status_code == 201
    story_id = r.json()["id"]
    async for session in get_test_db():
        result = await session.execute(select(Story).where(Story.id == story_id))
        story = result.scalar_one()
        expires = (
            story.expires_at.replace(tzinfo=None)
            if story.expires_at.tzinfo
            else story.expires_at
        )
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
    await client.post(
        "/api/v1/communities",
        headers=alice_h,
        json={"name": "general", "description": "Test"},
    )
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

    await client.post(
        "/api/v1/communities",
        headers=alice_h,
        json={"name": "tech", "description": "Tech"},
    )
    await client.post("/api/v1/communities/tech/join", headers=bob_h)

    comm_r = await client.get("/api/v1/communities/tech")
    comm_id = comm_r.json()["id"]

    await client.post(
        "/api/v1/posts",
        headers=alice_h,
        json={"title": "Community post", "content": "hello", "community_id": comm_id},
    )

    r = await client.get("/api/v1/feed", headers=bob_h)
    assert r.status_code == 200
    titles = [p["title"] for p in r.json()]
    assert "Community post" in titles


@pytest.mark.asyncio
async def test_feed_deduplicates_followed_author_in_joined_community(client):
    """A post from a followed user in a joined community appears only once."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    await client.post(
        "/api/v1/communities",
        headers=alice_h,
        json={"name": "tech", "description": "Tech"},
    )
    await client.post("/api/v1/communities/tech/join", headers=bob_h)
    await client.post("/api/v1/users/alice/follow", headers=bob_h)

    comm_r = await client.get("/api/v1/communities/tech")
    comm_id = comm_r.json()["id"]

    await client.post(
        "/api/v1/posts",
        headers=alice_h,
        json={"title": "Dedup test", "content": "x", "community_id": comm_id},
    )

    r = await client.get("/api/v1/feed", headers=bob_h)
    titles = [p["title"] for p in r.json()]
    assert titles.count("Dedup test") == 1


@pytest.mark.asyncio
async def test_feed_excludes_unjoined_community_posts(client):
    """Posts in communities the viewer hasn't joined do not appear."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    await client.post(
        "/api/v1/communities",
        headers=alice_h,
        json={"name": "secret", "description": "S"},
    )
    comm_r = await client.get("/api/v1/communities/secret")
    comm_id = comm_r.json()["id"]

    await client.post(
        "/api/v1/posts",
        headers=alice_h,
        json={"title": "Not for bob", "content": "x", "community_id": comm_id},
    )

    r = await client.get("/api/v1/feed", headers=bob_h)
    titles = [p["title"] for p in r.json()]
    assert "Not for bob" not in titles


# ---------------------------------------------------------------------------
# Link stories
# ---------------------------------------------------------------------------

_OG_RESULT = {
    "title": "Example Page",
    "description": "A test page",
    "image": "https://example.com/og.jpg",
    "site_name": "Example",
}


@pytest.mark.asyncio
async def test_create_link_only_story(client):
    hdrs = await setup_user(client, "alice")
    with patch(
        "app.api.v1.stories.fetch_og_metadata",
        new_callable=AsyncMock,
        return_value=_OG_RESULT,
    ):
        r = await _make_story(
            client, hdrs, image_url=None, link_url="https://example.com"
        )
    assert r.status_code == 201
    body = r.json()
    assert body["media_type"] == "link"
    assert body["image_url"] is None
    assert body["link_preview"]["url"] == "https://example.com"
    assert body["link_preview"]["title"] == "Example Page"


@pytest.mark.asyncio
async def test_create_image_and_link_story(client):
    hdrs = await setup_user(client, "alice")
    with patch(
        "app.api.v1.stories.fetch_og_metadata",
        new_callable=AsyncMock,
        return_value=_OG_RESULT,
    ):
        r = await _make_story(
            client,
            hdrs,
            image_url="https://cdn.example.com/img.webp",
            link_url="https://example.com",
        )
    assert r.status_code == 201
    body = r.json()
    assert body["media_type"] == "link_image"
    assert body["image_url"] == "https://cdn.example.com/img.webp"
    assert body["link_preview"]["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_create_story_no_image_no_link_is_422(client):
    hdrs = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/stories",
        headers=hdrs,
        json={
            "duration_hours": 24,
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_image_only_story_backward_compat(client):
    """Existing image-only story creation still works and returns new fields."""
    hdrs = await setup_user(client, "alice")
    r = await _make_story(client, hdrs, caption="old style")
    assert r.status_code == 201
    body = r.json()
    assert body["media_type"] == "image"
    assert body["link_preview"] is None
    assert body["mentions"] == []


@pytest.mark.asyncio
async def test_feed_returns_link_preview(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await client.post("/api/v1/users/alice/follow", headers=bob_h)

    with patch(
        "app.api.v1.stories.fetch_og_metadata",
        new_callable=AsyncMock,
        return_value=_OG_RESULT,
    ):
        await _make_story(
            client, alice_h, image_url=None, link_url="https://example.com"
        )

    r = await client.get("/api/v1/stories/feed", headers=bob_h)
    assert r.status_code == 200
    stories = r.json()
    assert len(stories) >= 1
    assert stories[0]["link_preview"]["title"] == "Example Page"
    assert stories[0]["media_type"] == "link"


# ---------------------------------------------------------------------------
# @mention tagging
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mention_creates_story_mention_row(client):
    alice_h = await setup_user(client, "alice")
    await setup_user(client, "bob")

    r = await _make_story(client, alice_h, caption="Hey @bob check this")
    assert r.status_code == 201
    body = r.json()
    assert len(body["mentions"]) == 1
    assert body["mentions"][0]["username"] == "bob"

    # Verify DB row
    async for session in get_test_db():
        result = await session.execute(
            select(StoryMention).where(StoryMention.story_id == body["id"])
        )
        mentions = result.scalars().all()
        assert len(mentions) == 1


@pytest.mark.asyncio
async def test_mention_nonexistent_user_is_silently_skipped(client):
    alice_h = await setup_user(client, "alice")

    r = await _make_story(client, alice_h, caption="Hey @nobody123")
    assert r.status_code == 201
    assert r.json()["mentions"] == []


@pytest.mark.asyncio
async def test_mention_sends_notification(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    await _make_story(client, alice_h, caption="Hi @bob!")

    r = await client.get("/api/v1/notifications", headers=bob_h)
    assert r.status_code == 200
    notifs = r.json()
    story_mentions = [n for n in notifs if n["type"] == "story_mention"]
    assert len(story_mentions) >= 1


@pytest.mark.asyncio
async def test_self_mention_no_notification(client):
    alice_h = await setup_user(client, "alice")

    await _make_story(client, alice_h, caption="Me @alice")

    r = await client.get("/api/v1/notifications", headers=alice_h)
    story_mentions = [n for n in r.json() if n["type"] == "story_mention"]
    assert len(story_mentions) == 0


@pytest.mark.asyncio
async def test_mentions_capped_at_max(client):
    """Only story_max_mentions users are mentioned, rest are ignored."""
    alice_h = await setup_user(client, "alice")
    # Create 7 users
    for i in range(7):
        await setup_user(client, f"user{i}")

    caption = " ".join(f"@user{i}" for i in range(7))
    r = await _make_story(client, alice_h, caption=caption)
    assert r.status_code == 201
    # Default max is 5
    assert len(r.json()["mentions"]) <= 5


@pytest.mark.asyncio
async def test_delete_story_removes_story(client):
    """Deleting a story removes it from the database. In production (PostgreSQL),
    CASCADE also deletes StoryMention rows; SQLite doesn't enforce this."""
    alice_h = await setup_user(client, "alice")
    await setup_user(client, "bob")

    r = await _make_story(client, alice_h, caption="Hey @bob")
    story_id = r.json()["id"]

    resp = await client.delete(f"/api/v1/stories/{story_id}", headers=alice_h)
    assert resp.status_code == 204

    async for session in get_test_db():
        result = await session.execute(select(Story).where(Story.id == story_id))
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_feed_returns_mentions(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await setup_user(client, "carol")
    await client.post("/api/v1/users/alice/follow", headers=bob_h)

    await _make_story(client, alice_h, caption="With @carol")

    r = await client.get("/api/v1/stories/feed", headers=bob_h)
    stories = r.json()
    assert len(stories) >= 1
    assert stories[0]["mentions"][0]["username"] == "carol"


# ---------------------------------------------------------------------------
# User autocomplete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_autocomplete(client):
    hdrs = await setup_user(client, "alice")
    await setup_user(client, "bob")
    await setup_user(client, "bobby")

    r = await client.get(
        "/api/v1/users/autocomplete", headers=hdrs, params={"q": "bob"}
    )
    assert r.status_code == 200
    usernames = [u["username"] for u in r.json()]
    assert "bob" in usernames
    assert "bobby" in usernames
    assert "alice" not in usernames


@pytest.mark.asyncio
async def test_user_autocomplete_requires_auth(client):
    r = await client.get("/api/v1/users/autocomplete", params={"q": "a"})
    assert r.status_code == 401
