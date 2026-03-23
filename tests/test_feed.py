from tests.conftest import setup_user


async def test_feed_empty(client):
    h = await setup_user(client, "alice")
    r = await client.get("/api/v1/feed", headers=h)
    assert r.status_code == 200
    assert r.json() == []


async def test_feed_shows_followed_user_posts(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    # Bob creates a post
    await client.post("/api/v1/posts", headers=bob_h, json={
        "title": "Bob's post", "content": "Hello from bob"
    })

    # Alice doesn't follow bob yet — feed should be empty
    r = await client.get("/api/v1/feed", headers=alice_h)
    assert r.json() == []

    # Alice follows bob
    await client.post("/api/v1/users/bob/follow", headers=alice_h)

    # Now alice's feed should include bob's post
    r = await client.get("/api/v1/feed", headers=alice_h)
    assert r.status_code == 200
    posts = r.json()
    assert len(posts) == 1
    assert posts[0]["title"] == "Bob's post"


async def test_feed_is_chronological(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await client.post("/api/v1/users/bob/follow", headers=alice_h)

    await client.post("/api/v1/posts", headers=bob_h, json={"title": "First", "content": "1"})
    await client.post("/api/v1/posts", headers=bob_h, json={"title": "Second", "content": "2"})
    await client.post("/api/v1/posts", headers=bob_h, json={"title": "Third", "content": "3"})

    r = await client.get("/api/v1/feed", headers=alice_h)
    titles = [p["title"] for p in r.json()]
    # Feed is newest first
    assert titles == ["Third", "Second", "First"]


async def test_feed_does_not_show_own_posts(client):
    alice_h = await setup_user(client, "alice")
    await client.post("/api/v1/posts", headers=alice_h, json={
        "title": "My own post", "content": "This is mine"
    })
    r = await client.get("/api/v1/feed", headers=alice_h)
    assert r.json() == []


async def test_feed_unauthenticated(client):
    r = await client.get("/api/v1/feed")
    assert r.status_code == 401
