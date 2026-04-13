"""Tests for sharing posts via DM (shared_post_id on messages)."""

import pytest

from tests.conftest import setup_user


@pytest.mark.anyio
async def test_send_dm_with_shared_post(client):
    """Sending a DM with shared_post_id stores the reference and enriches it on read."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    bob_me = await client.get("/api/v1/users/me", headers=bob_h)
    bob_id = bob_me.json()["id"]

    # Alice creates a public post
    post_r = await client.post(
        "/api/v1/posts",
        headers=alice_h,
        json={"title": "Hello world", "content": "Test content"},
    )
    assert post_r.status_code == 201
    post_id = post_r.json()["id"]

    # Alice sends the post as a DM to Bob
    msg_r = await client.post(
        "/api/v1/messages",
        headers=alice_h,
        json={
            "recipient_id": bob_id,
            "ciphertext": "Check this out!",
            "device_keys": [],
            "shared_post_id": post_id,
        },
    )
    assert msg_r.status_code == 201
    assert msg_r.json()["shared_post_id"] == post_id

    # Bob retrieves the conversation — shared_post should be enriched
    alice_me = await client.get("/api/v1/users/me", headers=alice_h)
    alice_id = alice_me.json()["id"]

    conv_r = await client.get(f"/api/v1/messages/{alice_id}", headers=bob_h)
    assert conv_r.status_code == 200
    messages = conv_r.json()
    assert len(messages) == 1
    msg = messages[0]
    assert msg["shared_post_id"] == post_id
    assert msg["shared_post"] is not None
    assert msg["shared_post"]["title"] == "Hello world"
    assert msg["shared_post"]["author_username"] == "alice"


@pytest.mark.anyio
async def test_send_dm_with_invalid_shared_post(client):
    """Sending a DM with a non-existent shared_post_id returns 404."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_me = await client.get("/api/v1/users/me", headers=bob_h)
    bob_id = bob_me.json()["id"]

    r = await client.post(
        "/api/v1/messages",
        headers=alice_h,
        json={
            "recipient_id": bob_id,
            "ciphertext": "Check this out!",
            "device_keys": [],
            "shared_post_id": 99999,
        },
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Shared post not found"


@pytest.mark.anyio
async def test_send_dm_without_shared_post(client):
    """Sending a regular DM still works — shared_post fields are null."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_me = await client.get("/api/v1/users/me", headers=bob_h)
    bob_id = bob_me.json()["id"]

    r = await client.post(
        "/api/v1/messages",
        headers=alice_h,
        json={
            "recipient_id": bob_id,
            "ciphertext": "Just a normal message",
            "device_keys": [],
        },
    )
    assert r.status_code == 201
    assert r.json()["shared_post_id"] is None

    # Conversation should not have shared_post
    alice_me = await client.get("/api/v1/users/me", headers=alice_h)
    alice_id = alice_me.json()["id"]
    conv_r = await client.get(f"/api/v1/messages/{alice_id}", headers=bob_h)
    msgs = conv_r.json()
    assert len(msgs) == 1
    assert msgs[0]["shared_post"] is None
