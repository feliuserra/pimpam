"""Tests for user blocking: block, unblock, list, and effects on follow/messages/feed."""

from tests.conftest import register, setup_user


async def test_block_user(client):
    alice_h = await setup_user(client, "alice")
    await register(client, "bob")
    r = await client.post("/api/v1/users/bob/block", headers=alice_h)
    assert r.status_code == 204


async def test_block_self(client):
    alice_h = await setup_user(client, "alice")
    r = await client.post("/api/v1/users/alice/block", headers=alice_h)
    assert r.status_code == 400


async def test_block_nonexistent_user(client):
    alice_h = await setup_user(client, "alice")
    r = await client.post("/api/v1/users/nobody/block", headers=alice_h)
    assert r.status_code == 404


async def test_double_block(client):
    alice_h = await setup_user(client, "alice")
    await register(client, "bob")
    await client.post("/api/v1/users/bob/block", headers=alice_h)
    r = await client.post("/api/v1/users/bob/block", headers=alice_h)
    assert r.status_code == 409


async def test_unblock_user(client):
    alice_h = await setup_user(client, "alice")
    await register(client, "bob")
    await client.post("/api/v1/users/bob/block", headers=alice_h)
    r = await client.delete("/api/v1/users/bob/block", headers=alice_h)
    assert r.status_code == 204


async def test_unblock_not_blocked(client):
    alice_h = await setup_user(client, "alice")
    await register(client, "bob")
    r = await client.delete("/api/v1/users/bob/block", headers=alice_h)
    assert r.status_code == 404


async def test_list_blocked_users(client):
    alice_h = await setup_user(client, "alice")
    await register(client, "bob")
    await register(client, "carol")
    await client.post("/api/v1/users/bob/block", headers=alice_h)
    await client.post("/api/v1/users/carol/block", headers=alice_h)
    r = await client.get("/api/v1/users/me/blocked", headers=alice_h)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    usernames = {b["blocked_username"] for b in data}
    assert usernames == {"bob", "carol"}


async def test_list_blocked_empty(client):
    alice_h = await setup_user(client, "alice")
    r = await client.get("/api/v1/users/me/blocked", headers=alice_h)
    assert r.status_code == 200
    assert r.json() == []


async def test_block_removes_follow(client):
    """Blocking someone removes follows in both directions."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    # Alice follows Bob
    await client.post("/api/v1/users/bob/follow", headers=alice_h)
    # Bob follows Alice
    await client.post("/api/v1/users/alice/follow", headers=bob_h)

    # Alice blocks Bob
    await client.post("/api/v1/users/bob/block", headers=alice_h)

    # Verify Alice no longer follows Bob
    profile = await client.get("/api/v1/users/bob", headers=alice_h)
    assert profile.json()["follower_count"] == 0

    # Verify Bob no longer follows Alice
    profile = await client.get("/api/v1/users/alice", headers=bob_h)
    assert profile.json()["follower_count"] == 0


async def test_blocked_user_cannot_follow(client):
    """A blocked user cannot follow the blocker."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await client.post("/api/v1/users/bob/block", headers=alice_h)
    r = await client.post("/api/v1/users/alice/follow", headers=bob_h)
    assert r.status_code == 403


async def test_blocker_cannot_follow_blocked(client):
    """The blocker also cannot follow the blocked user (while block is active)."""
    alice_h = await setup_user(client, "alice")
    await register(client, "bob")
    await client.post("/api/v1/users/bob/block", headers=alice_h)
    r = await client.post("/api/v1/users/bob/follow", headers=alice_h)
    assert r.status_code == 403


async def test_blocked_user_cannot_message(client):
    """A blocked user cannot send a message to the blocker."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await client.post("/api/v1/users/bob/block", headers=alice_h)

    # Get Alice's user id
    alice_profile = await client.get("/api/v1/users/me", headers=alice_h)
    alice_id = alice_profile.json()["id"]

    r = await client.post(
        "/api/v1/messages",
        headers=bob_h,
        json={
            "recipient_id": alice_id,
            "ciphertext": "hello",
            "encrypted_key": "key1",
            "sender_encrypted_key": "key2",
        },
    )
    assert r.status_code == 403


async def test_blocker_cannot_message_blocked(client):
    """The blocker also cannot send a message to the blocked user."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await client.post("/api/v1/users/bob/block", headers=alice_h)

    bob_profile = await client.get("/api/v1/users/me", headers=bob_h)
    bob_id = bob_profile.json()["id"]

    r = await client.post(
        "/api/v1/messages",
        headers=alice_h,
        json={
            "recipient_id": bob_id,
            "ciphertext": "hello",
            "encrypted_key": "key1",
            "sender_encrypted_key": "key2",
        },
    )
    assert r.status_code == 403


async def test_blocked_user_posts_hidden_from_feed(client):
    """Posts by blocked users should not appear in the feed."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    # Alice follows Bob
    await client.post("/api/v1/users/bob/follow", headers=alice_h)

    # Bob creates a post
    await client.post(
        "/api/v1/posts",
        headers=bob_h,
        json={"title": "Bob's post", "content": "Hello from Bob"},
    )

    # Alice can see it in feed
    r = await client.get("/api/v1/feed", headers=alice_h)
    assert len(r.json()) == 1

    # Alice blocks Bob
    await client.post("/api/v1/users/bob/block", headers=alice_h)

    # Bob's post should no longer appear in feed
    r = await client.get("/api/v1/feed", headers=alice_h)
    assert len(r.json()) == 0


async def test_unblock_allows_follow_again(client):
    """After unblocking, the user can be followed again."""
    alice_h = await setup_user(client, "alice")
    await register(client, "bob")
    await client.post("/api/v1/users/bob/block", headers=alice_h)
    await client.delete("/api/v1/users/bob/block", headers=alice_h)
    r = await client.post("/api/v1/users/bob/follow", headers=alice_h)
    assert r.status_code == 204
