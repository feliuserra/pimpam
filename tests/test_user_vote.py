"""Tests for the user_vote field on PostPublic responses."""

from tests.conftest import setup_user


async def test_create_post_returns_author_vote(client):
    """Creating a post returns user_vote=1 (author's automatic upvote)."""
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/posts", headers=h, json={"title": "My post", "content": "Hello"}
    )
    assert r.status_code == 201
    assert r.json()["user_vote"] == 1


async def test_get_post_returns_user_vote_when_voted(client):
    """Getting a post returns the viewer's vote direction."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    r = await client.post(
        "/api/v1/posts", headers=alice_h, json={"title": "Post", "content": "Content"}
    )
    post_id = r.json()["id"]

    # Bob upvotes
    await client.post(
        f"/api/v1/posts/{post_id}/vote", headers=bob_h, json={"direction": 1}
    )

    # Bob fetches the post — should see user_vote=1
    r = await client.get(f"/api/v1/posts/{post_id}", headers=bob_h)
    assert r.status_code == 200
    assert r.json()["user_vote"] == 1


async def test_get_post_returns_null_vote_when_not_voted(client):
    """Getting a post without having voted returns user_vote=None."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    r = await client.post(
        "/api/v1/posts", headers=alice_h, json={"title": "Post", "content": "Content"}
    )
    post_id = r.json()["id"]

    r = await client.get(f"/api/v1/posts/{post_id}", headers=bob_h)
    assert r.status_code == 200
    assert r.json()["user_vote"] is None


async def test_get_post_returns_null_vote_when_unauthenticated(client):
    """Getting a post without authentication returns user_vote=None."""
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/posts", headers=h, json={"title": "Post", "content": "Content"}
    )
    post_id = r.json()["id"]

    r = await client.get(f"/api/v1/posts/{post_id}")
    assert r.status_code == 200
    assert r.json()["user_vote"] is None


async def test_get_post_returns_downvote(client):
    """A downvote is returned as user_vote=-1."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    r = await client.post(
        "/api/v1/posts", headers=alice_h, json={"title": "Post", "content": "Content"}
    )
    post_id = r.json()["id"]

    await client.post(
        f"/api/v1/posts/{post_id}/vote", headers=bob_h, json={"direction": -1}
    )

    r = await client.get(f"/api/v1/posts/{post_id}", headers=bob_h)
    assert r.json()["user_vote"] == -1


async def test_feed_includes_user_vote(client):
    """Feed posts include the viewer's vote direction."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await client.post("/api/v1/users/bob/follow", headers=alice_h)

    # Bob creates two posts
    r1 = await client.post(
        "/api/v1/posts", headers=bob_h, json={"title": "Post 1", "content": "A"}
    )
    await client.post(
        "/api/v1/posts", headers=bob_h, json={"title": "Post 2", "content": "B"}
    )

    # Alice upvotes post 1 only
    await client.post(
        f"/api/v1/posts/{r1.json()['id']}/vote",
        headers=alice_h,
        json={"direction": 1},
    )

    r = await client.get("/api/v1/feed", headers=alice_h)
    posts = r.json()
    votes = {p["title"]: p["user_vote"] for p in posts}
    assert votes["Post 1"] == 1
    assert votes["Post 2"] is None


async def test_edit_post_returns_user_vote(client):
    """Editing a post returns user_vote for the author."""
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/posts", headers=h, json={"title": "Original", "content": "Body"}
    )
    post_id = r.json()["id"]

    r = await client.patch(
        f"/api/v1/posts/{post_id}", headers=h, json={"title": "Edited"}
    )
    assert r.status_code == 200
    assert r.json()["user_vote"] == 1


async def test_community_posts_include_user_vote(client):
    """Community post list includes user_vote for the viewer."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    # Alice creates a community
    await client.post(
        "/api/v1/communities", headers=alice_h, json={"name": "testcommunity"}
    )
    cid_r = await client.get("/api/v1/communities/testcommunity")
    cid = cid_r.json()["id"]

    # Alice creates a post in the community
    r = await client.post(
        "/api/v1/posts",
        headers=alice_h,
        json={"title": "Community post", "content": "Hi", "community_id": cid},
    )
    post_id = r.json()["id"]

    # Bob joins and upvotes
    await client.post("/api/v1/communities/testcommunity/join", headers=bob_h)
    await client.post(
        f"/api/v1/posts/{post_id}/vote", headers=bob_h, json={"direction": 1}
    )

    # Bob lists community posts — should see user_vote=1
    r = await client.get("/api/v1/communities/testcommunity/posts", headers=bob_h)
    assert r.status_code == 200
    posts = r.json()
    assert len(posts) == 1
    assert posts[0]["user_vote"] == 1


async def test_user_posts_include_user_vote(client):
    """User profile post list includes user_vote for the viewer."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    r = await client.post(
        "/api/v1/posts", headers=alice_h, json={"title": "Post", "content": "Content"}
    )
    post_id = r.json()["id"]

    await client.post(
        f"/api/v1/posts/{post_id}/vote", headers=bob_h, json={"direction": -1}
    )

    r = await client.get("/api/v1/users/alice/posts", headers=bob_h)
    assert r.status_code == 200
    assert r.json()[0]["user_vote"] == -1
