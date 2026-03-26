import pytest

from tests.conftest import setup_user

pytestmark = pytest.mark.asyncio


async def _create_community(client, auth, name):
    r = await client.post(
        "/api/v1/communities",
        json={"name": name, "description": "test"},
        headers=auth,
    )
    assert r.status_code == 201
    return r.json()


async def _create_post(client, auth, title="Test", community_id=None):
    data = {"title": title, "content": "content"}
    if community_id:
        data["community_id"] = community_id
    r = await client.post("/api/v1/posts", json=data, headers=auth)
    assert r.status_code == 201
    return r.json()


async def test_empty_feed_no_subscriptions(client):
    auth = await setup_user(client, "alice")
    r = await client.get("/api/v1/feed/for-you", headers=auth)
    assert r.status_code == 200
    assert r.json() == []


async def test_hashtag_posts_appear(client):
    alice = await setup_user(client, "alice")
    bob = await setup_user(client, "bob")

    # Bob creates a post with #photography
    await _create_post(client, bob, "#photography sunset")

    # Alice subscribes to #photography
    await client.post("/api/v1/hashtags/photography/subscribe", headers=alice)

    # Alice's For You feed should show Bob's post
    r = await client.get("/api/v1/feed/for-you", headers=alice)
    assert r.status_code == 200
    posts = r.json()
    assert len(posts) == 1
    assert posts[0]["attribution"] is not None
    assert any(
        a["type"] == "hashtag" and a["hashtag"] == "photography"
        for a in posts[0]["attribution"]
    )


async def test_curated_picks_appear(client):
    mod = await setup_user(client, "mod")
    member = await setup_user(client, "member")

    # Mod creates community and a post
    community = await _create_community(client, mod, "design")
    comm_id = community["id"]
    post = await _create_post(client, mod, "Great design tips", comm_id)

    # Member joins community
    await client.post("/api/v1/communities/design/join", headers=member)

    # Mod picks the post
    await client.post(
        "/api/v1/communities/design/picks",
        json={"post_id": post["id"], "note": "Must read"},
        headers=mod,
    )

    # Member's For You feed should show the picked post
    r = await client.get("/api/v1/feed/for-you", headers=member)
    assert r.status_code == 200
    posts = r.json()
    assert len(posts) == 1
    assert any(
        a["type"] == "pick" and a["curator_username"] == "mod"
        for a in posts[0]["attribution"]
    )


async def test_chronological_order(client):
    alice = await setup_user(client, "alice")
    bob = await setup_user(client, "bob")

    p1 = await _create_post(client, bob, "#tech first post")
    p2 = await _create_post(client, bob, "#tech second post")

    await client.post("/api/v1/hashtags/tech/subscribe", headers=alice)

    r = await client.get("/api/v1/feed/for-you", headers=alice)
    posts = r.json()
    assert len(posts) == 2
    # Newest first
    assert posts[0]["id"] == p2["id"]
    assert posts[1]["id"] == p1["id"]


async def test_unauthenticated_returns_401(client):
    r = await client.get("/api/v1/feed/for-you")
    assert r.status_code in (401, 403)


async def test_pagination(client):
    alice = await setup_user(client, "alice")
    bob = await setup_user(client, "bob")

    # Create posts with hashtag
    post_ids = []
    for i in range(5):
        p = await _create_post(client, bob, f"#code post {i}")
        post_ids.append(p["id"])

    await client.post("/api/v1/hashtags/code/subscribe", headers=alice)

    # First page
    r = await client.get("/api/v1/feed/for-you?limit=3", headers=alice)
    page1 = r.json()
    assert len(page1) == 3

    # Second page
    r = await client.get(
        f"/api/v1/feed/for-you?limit=3&before_id={page1[-1]['id']}",
        headers=alice,
    )
    page2 = r.json()
    assert len(page2) == 2

    # No overlap
    page1_ids = {p["id"] for p in page1}
    page2_ids = {p["id"] for p in page2}
    assert page1_ids.isdisjoint(page2_ids)
