"""
Integration tests for user profile social graph enrichment.

Covers follower/following counts, is_following flag, and
GET /users/{username}/followers, /following, /posts endpoints.
"""
import pytest

from tests.conftest import setup_user


# ---------------------------------------------------------------------------
# Counts on /me and /users/{username}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_me_includes_counts(client):
    hdrs = await setup_user(client, "alice")
    r = await client.get("/api/v1/users/me", headers=hdrs)
    assert r.status_code == 200
    data = r.json()
    assert "follower_count" in data
    assert "following_count" in data
    assert data["follower_count"] == 0
    assert data["following_count"] == 0


@pytest.mark.asyncio
async def test_follower_count_accurate(client):
    hdrs_alice = await setup_user(client, "alice")
    hdrs_bob = await setup_user(client, "bob")
    hdrs_carol = await setup_user(client, "carol")

    # Bob and Carol follow Alice
    await client.post("/api/v1/users/alice/follow", headers=hdrs_bob)
    await client.post("/api/v1/users/alice/follow", headers=hdrs_carol)

    r = await client.get("/api/v1/users/alice", headers=hdrs_alice)
    assert r.json()["follower_count"] == 2
    assert r.json()["following_count"] == 0


@pytest.mark.asyncio
async def test_following_count_accurate(client):
    hdrs_alice = await setup_user(client, "alice")
    await setup_user(client, "bob")
    await setup_user(client, "carol")

    await client.post("/api/v1/users/bob/follow", headers=hdrs_alice)
    await client.post("/api/v1/users/carol/follow", headers=hdrs_alice)

    r = await client.get("/api/v1/users/alice", headers=hdrs_alice)
    assert r.json()["following_count"] == 2


@pytest.mark.asyncio
async def test_is_following_true(client):
    hdrs_alice = await setup_user(client, "alice")
    hdrs_bob = await setup_user(client, "bob")

    await client.post("/api/v1/users/alice/follow", headers=hdrs_bob)

    r = await client.get("/api/v1/users/alice", headers=hdrs_bob)
    assert r.json()["is_following"] is True


@pytest.mark.asyncio
async def test_is_following_false(client):
    hdrs_alice = await setup_user(client, "alice")
    hdrs_bob = await setup_user(client, "bob")

    r = await client.get("/api/v1/users/alice", headers=hdrs_bob)
    assert r.json()["is_following"] is False


@pytest.mark.asyncio
async def test_is_following_none_own_profile(client):
    hdrs_alice = await setup_user(client, "alice")
    r = await client.get("/api/v1/users/alice", headers=hdrs_alice)
    assert r.json()["is_following"] is None


@pytest.mark.asyncio
async def test_is_following_none_unauthenticated(client):
    await setup_user(client, "alice")
    r = await client.get("/api/v1/users/alice")
    assert r.status_code == 200
    assert r.json()["is_following"] is None


# ---------------------------------------------------------------------------
# Followers / Following list endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_followers(client):
    hdrs_alice = await setup_user(client, "alice")
    hdrs_bob = await setup_user(client, "bob")
    await setup_user(client, "carol")
    hdrs_carol = hdrs_bob  # re-use login pattern

    # Bob follows Alice
    await client.post("/api/v1/users/alice/follow", headers=hdrs_bob)

    r = await client.get("/api/v1/users/alice/followers", headers=hdrs_alice)
    assert r.status_code == 200
    usernames = [u["username"] for u in r.json()]
    assert "bob" in usernames


@pytest.mark.asyncio
async def test_list_followers_empty(client):
    hdrs_alice = await setup_user(client, "alice")
    r = await client.get("/api/v1/users/alice/followers", headers=hdrs_alice)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_following(client):
    hdrs_alice = await setup_user(client, "alice")
    await setup_user(client, "bob")

    await client.post("/api/v1/users/bob/follow", headers=hdrs_alice)

    r = await client.get("/api/v1/users/alice/following", headers=hdrs_alice)
    assert r.status_code == 200
    usernames = [u["username"] for u in r.json()]
    assert "bob" in usernames


@pytest.mark.asyncio
async def test_list_followers_404(client):
    hdrs_alice = await setup_user(client, "alice")
    r = await client.get("/api/v1/users/nobody/followers", headers=hdrs_alice)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_following_404(client):
    hdrs_alice = await setup_user(client, "alice")
    r = await client.get("/api/v1/users/nobody/following", headers=hdrs_alice)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# User posts endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_user_posts(client):
    hdrs_alice = await setup_user(client, "alice")

    await client.post("/api/v1/posts", json={"title": "Post 1", "content": "hello"}, headers=hdrs_alice)
    await client.post("/api/v1/posts", json={"title": "Post 2", "content": "world"}, headers=hdrs_alice)

    r = await client.get("/api/v1/users/alice/posts")
    assert r.status_code == 200
    titles = [p["title"] for p in r.json()]
    assert "Post 1" in titles
    assert "Post 2" in titles


@pytest.mark.asyncio
async def test_list_user_posts_public_only(client):
    hdrs_alice = await setup_user(client, "alice")

    # Public post
    await client.post("/api/v1/posts", json={"title": "Public", "content": "hi"}, headers=hdrs_alice)

    # Group post
    cf = (await client.get("/api/v1/friend-groups/close-friends", headers=hdrs_alice)).json()
    await client.post("/api/v1/posts", json={
        "title": "Private",
        "content": "secret",
        "visibility": "group",
        "friend_group_id": cf["id"],
    }, headers=hdrs_alice)

    r = await client.get("/api/v1/users/alice/posts")
    assert r.status_code == 200
    titles = [p["title"] for p in r.json()]
    assert "Public" in titles
    assert "Private" not in titles


@pytest.mark.asyncio
async def test_list_user_posts_removed_excluded(client):
    hdrs_alice = await setup_user(client, "alice")

    r_post = await client.post("/api/v1/posts", json={"title": "ToDelete", "content": "bye"}, headers=hdrs_alice)
    post_id = r_post.json()["id"]
    await client.delete(f"/api/v1/posts/{post_id}", headers=hdrs_alice)

    r = await client.get("/api/v1/users/alice/posts")
    titles = [p["title"] for p in r.json()]
    assert "ToDelete" not in titles


@pytest.mark.asyncio
async def test_list_user_posts_pagination(client):
    hdrs_alice = await setup_user(client, "alice")

    post_ids = []
    for i in range(5):
        r = await client.post("/api/v1/posts", json={"title": f"Post {i}", "content": "x"}, headers=hdrs_alice)
        post_ids.append(r.json()["id"])

    # Get first 3
    r1 = await client.get("/api/v1/users/alice/posts?limit=3")
    page1 = r1.json()
    assert len(page1) == 3

    # Cursor to next page using the last post's id
    last_id = page1[-1]["id"]
    r2 = await client.get(f"/api/v1/users/alice/posts?limit=3&before_id={last_id}")
    page2 = r2.json()
    assert len(page2) == 2

    # No overlap
    ids1 = {p["id"] for p in page1}
    ids2 = {p["id"] for p in page2}
    assert ids1.isdisjoint(ids2)


@pytest.mark.asyncio
async def test_list_user_posts_404(client):
    r = await client.get("/api/v1/users/nobody/posts")
    assert r.status_code == 404
