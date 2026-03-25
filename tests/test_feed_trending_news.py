"""
Tests for the trending and news feed endpoints.

GET /feed/trending — top posts by score (karma + 2×comment_count) in last N hours
GET /feed/news    — chronological posts from is_news communities, cursor-paginated
"""

from datetime import datetime, timedelta, timezone

from app.models.community import Community
from app.models.post import Post

from tests.conftest import get_test_db, setup_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_community(client, headers, name, is_news=False):
    """Create a community via API, then optionally set is_news directly in DB."""
    await client.post("/api/v1/communities", headers=headers, json={"name": name})
    r = await client.get(f"/api/v1/communities/{name}")
    community = r.json()

    if is_news:
        from sqlalchemy import select

        async for session in get_test_db():
            result = await session.execute(
                select(Community).where(Community.id == community["id"])
            )
            c = result.scalar_one()
            c.is_news = True
            await session.commit()

    return community


async def _create_post(client, headers, title, content="body", community_id=None):
    """Create a post via API. Returns the response JSON."""
    payload = {"title": title, "content": content}
    if community_id is not None:
        payload["community_id"] = community_id
    r = await client.post("/api/v1/posts", headers=headers, json=payload)
    assert r.status_code == 201, r.text
    return r.json()


async def _vote_post(client, headers, post_id, direction=1):
    """Cast a vote on a post."""
    r = await client.post(
        f"/api/v1/posts/{post_id}/vote",
        headers=headers,
        json={"direction": direction},
    )
    return r


async def _add_comment(client, headers, post_id, content="A comment"):
    """Add a comment to a post."""
    r = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        headers=headers,
        json={"content": content},
    )
    return r


async def _set_post_created_at(post_id, dt):
    """Directly set a post's created_at timestamp in the DB."""
    from sqlalchemy import select

    async for session in get_test_db():
        result = await session.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one()
        post.created_at = dt
        await session.commit()


async def _set_post_removed(post_id):
    """Mark a post as removed directly in the DB."""
    from sqlalchemy import select

    async for session in get_test_db():
        result = await session.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one()
        post.is_removed = True
        await session.commit()


# ===========================================================================
# Trending feed tests
# ===========================================================================


async def test_trending_returns_posts_ordered_by_score(client):
    """Posts with higher score (karma + 2×comment_count) rank higher."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    carol_h = await setup_user(client, "carol")

    # Post A: karma=1 (default), 0 comments -> score=1
    await _create_post(client, alice_h, "Low score")

    # Post B: karma=1 + 1 upvote = 2, 0 comments -> score=2
    post_b = await _create_post(client, alice_h, "Medium score")
    await _vote_post(client, bob_h, post_b["id"], direction=1)

    # Post C: karma=1, 2 comments -> score=1 + 2×2 = 5
    post_c = await _create_post(client, alice_h, "High score")
    await _add_comment(client, bob_h, post_c["id"], "comment 1")
    await _add_comment(client, carol_h, post_c["id"], "comment 2")

    r = await client.get("/api/v1/feed/trending")
    assert r.status_code == 200
    titles = [p["title"] for p in r.json()]
    assert titles[0] == "High score"
    assert titles[1] == "Medium score"
    assert titles[2] == "Low score"


async def test_trending_respects_time_window(client):
    """Posts older than the hours window are excluded."""
    alice_h = await setup_user(client, "alice")

    # Create a recent post
    await _create_post(client, alice_h, "Recent post")

    # Create an old post and backdate it to 48 hours ago
    old = await _create_post(client, alice_h, "Old post")
    old_time = datetime.now(timezone.utc) - timedelta(hours=48)
    await _set_post_created_at(old["id"], old_time)

    # Default window is 24h — only the recent post should appear
    r = await client.get("/api/v1/feed/trending")
    assert r.status_code == 200
    titles = [p["title"] for p in r.json()]
    assert "Recent post" in titles
    assert "Old post" not in titles


async def test_trending_custom_hours_includes_older_posts(client):
    """With a wider time window, older posts are included."""
    alice_h = await setup_user(client, "alice")

    await _create_post(client, alice_h, "Recent post")

    old = await _create_post(client, alice_h, "Old post")
    old_time = datetime.now(timezone.utc) - timedelta(hours=48)
    await _set_post_created_at(old["id"], old_time)

    # With hours=72, both posts should appear
    r = await client.get("/api/v1/feed/trending?hours=72")
    assert r.status_code == 200
    titles = [p["title"] for p in r.json()]
    assert "Recent post" in titles
    assert "Old post" in titles


async def test_trending_excludes_removed_posts(client):
    """Removed posts do not appear in trending."""
    alice_h = await setup_user(client, "alice")

    await _create_post(client, alice_h, "Visible post")
    removed = await _create_post(client, alice_h, "Removed post")
    await _set_post_removed(removed["id"])

    r = await client.get("/api/v1/feed/trending")
    assert r.status_code == 200
    titles = [p["title"] for p in r.json()]
    assert "Visible post" in titles
    assert "Removed post" not in titles


async def test_trending_works_unauthenticated(client):
    """Trending endpoint is accessible without authentication."""
    alice_h = await setup_user(client, "alice")
    await _create_post(client, alice_h, "Public post")

    r = await client.get("/api/v1/feed/trending")
    assert r.status_code == 200
    posts = r.json()
    assert len(posts) >= 1
    assert posts[0]["title"] == "Public post"


async def test_trending_works_authenticated(client):
    """Trending endpoint also works with a logged-in user."""
    alice_h = await setup_user(client, "alice")
    await _create_post(client, alice_h, "A post")

    bob_h = await setup_user(client, "bob")
    r = await client.get("/api/v1/feed/trending", headers=bob_h)
    assert r.status_code == 200
    assert len(r.json()) >= 1


async def test_trending_limit_param(client):
    """The limit parameter caps the number of returned posts."""
    alice_h = await setup_user(client, "alice")
    for i in range(5):
        await _create_post(client, alice_h, f"Post {i}", content=f"Content {i}")

    r = await client.get("/api/v1/feed/trending?limit=2")
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_trending_empty_when_no_posts(client):
    """Trending returns an empty list when there are no posts."""
    r = await client.get("/api/v1/feed/trending")
    assert r.status_code == 200
    assert r.json() == []


# ===========================================================================
# News feed tests
# ===========================================================================


async def test_news_returns_posts_from_news_communities(client):
    """News feed returns posts from communities with is_news=True."""
    alice_h = await setup_user(client, "alice")
    news_community = await _create_community(client, alice_h, "worldnews", is_news=True)

    await _create_post(
        client,
        alice_h,
        "Breaking news",
        content="Something happened",
        community_id=news_community["id"],
    )

    r = await client.get("/api/v1/feed/news")
    assert r.status_code == 200
    posts = r.json()
    assert len(posts) == 1
    assert posts[0]["title"] == "Breaking news"


async def test_news_excludes_non_news_communities(client):
    """Posts from non-news communities do not appear in the news feed."""
    alice_h = await setup_user(client, "alice")
    news_community = await _create_community(client, alice_h, "worldnews", is_news=True)
    regular_community = await _create_community(
        client, alice_h, "general", is_news=False
    )

    await _create_post(
        client,
        alice_h,
        "News post",
        community_id=news_community["id"],
    )
    await _create_post(
        client,
        alice_h,
        "Regular post",
        community_id=regular_community["id"],
    )

    r = await client.get("/api/v1/feed/news")
    assert r.status_code == 200
    titles = [p["title"] for p in r.json()]
    assert "News post" in titles
    assert "Regular post" not in titles


async def test_news_excludes_posts_without_community(client):
    """Posts not in any community do not appear in the news feed."""
    alice_h = await setup_user(client, "alice")
    await _create_post(client, alice_h, "Standalone post")

    r = await client.get("/api/v1/feed/news")
    assert r.status_code == 200
    assert r.json() == []


async def test_news_cursor_pagination(client):
    """News feed supports cursor-based pagination via before_id."""
    alice_h = await setup_user(client, "alice")
    news_community = await _create_community(client, alice_h, "worldnews", is_news=True)

    # Create 5 posts in chronological order
    post_ids = []
    for i in range(5):
        post = await _create_post(
            client,
            alice_h,
            f"News {i}",
            content=f"Content {i}",
            community_id=news_community["id"],
        )
        post_ids.append(post["id"])

    # Fetch first page (newest first)
    r = await client.get("/api/v1/feed/news?limit=3")
    assert r.status_code == 200
    page1 = r.json()
    assert len(page1) == 3
    # Newest first
    assert page1[0]["title"] == "News 4"
    assert page1[1]["title"] == "News 3"
    assert page1[2]["title"] == "News 2"

    # Fetch second page using before_id of the last item on page 1
    last_id = page1[-1]["id"]
    r = await client.get(f"/api/v1/feed/news?limit=3&before_id={last_id}")
    assert r.status_code == 200
    page2 = r.json()
    assert len(page2) == 2
    assert page2[0]["title"] == "News 1"
    assert page2[1]["title"] == "News 0"


async def test_news_works_unauthenticated(client):
    """News feed is accessible without authentication."""
    alice_h = await setup_user(client, "alice")
    news_community = await _create_community(client, alice_h, "worldnews", is_news=True)
    await _create_post(
        client,
        alice_h,
        "Public news",
        community_id=news_community["id"],
    )

    r = await client.get("/api/v1/feed/news")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["title"] == "Public news"


async def test_news_works_authenticated(client):
    """News feed also works with a logged-in user."""
    alice_h = await setup_user(client, "alice")
    news_community = await _create_community(client, alice_h, "worldnews", is_news=True)
    await _create_post(
        client,
        alice_h,
        "Auth news",
        community_id=news_community["id"],
    )

    bob_h = await setup_user(client, "bob")
    r = await client.get("/api/v1/feed/news", headers=bob_h)
    assert r.status_code == 200
    assert len(r.json()) >= 1


async def test_news_excludes_removed_posts(client):
    """Removed posts do not appear in the news feed."""
    alice_h = await setup_user(client, "alice")
    news_community = await _create_community(client, alice_h, "worldnews", is_news=True)

    await _create_post(
        client,
        alice_h,
        "Visible news",
        community_id=news_community["id"],
    )
    removed = await _create_post(
        client,
        alice_h,
        "Removed news",
        community_id=news_community["id"],
    )
    await _set_post_removed(removed["id"])

    r = await client.get("/api/v1/feed/news")
    assert r.status_code == 200
    titles = [p["title"] for p in r.json()]
    assert "Visible news" in titles
    assert "Removed news" not in titles


async def test_news_is_chronological_newest_first(client):
    """News feed returns posts in reverse chronological order."""
    alice_h = await setup_user(client, "alice")
    news_community = await _create_community(client, alice_h, "worldnews", is_news=True)

    await _create_post(
        client,
        alice_h,
        "First",
        community_id=news_community["id"],
    )
    await _create_post(
        client,
        alice_h,
        "Second",
        community_id=news_community["id"],
    )
    await _create_post(
        client,
        alice_h,
        "Third",
        community_id=news_community["id"],
    )

    r = await client.get("/api/v1/feed/news")
    assert r.status_code == 200
    titles = [p["title"] for p in r.json()]
    assert titles == ["Third", "Second", "First"]


async def test_news_empty_when_no_news_communities(client):
    """News feed returns empty list when no news communities exist."""
    r = await client.get("/api/v1/feed/news")
    assert r.status_code == 200
    assert r.json() == []


async def test_news_from_multiple_news_communities(client):
    """News feed aggregates posts from multiple is_news communities."""
    alice_h = await setup_user(client, "alice")
    news1 = await _create_community(client, alice_h, "worldnews", is_news=True)
    news2 = await _create_community(client, alice_h, "localnews", is_news=True)

    await _create_post(
        client,
        alice_h,
        "World story",
        community_id=news1["id"],
    )
    await _create_post(
        client,
        alice_h,
        "Local story",
        community_id=news2["id"],
    )

    r = await client.get("/api/v1/feed/news")
    assert r.status_code == 200
    titles = [p["title"] for p in r.json()]
    assert "World story" in titles
    assert "Local story" in titles
    assert len(titles) == 2
