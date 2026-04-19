"""Tests for sharing posts via DM (shared_post_id on messages)."""

import pytest

from tests.conftest import setup_user

# Valid RSA-2048 SPKI public key (base64-encoded DER) for device registration
VALID_SPKI = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAv06L2BLDCJpXoKQzty0i"
    "Ae9iSGYUFTQTiO0nplL1tQ/NOqwB3d5F16hCCJY3bkvs5rLEBO0M4dQLlgXt1iOt"
    "8pVMiZGUBDiU7EUxVfgiIl9OKSWCNMaFz46uUiIQpWVXAHT1RkXAuVO63aibvmA1"
    "IaHMZ6gOePlzqVyCqFPpHbb+ktDAD3s5GTCQHYTL3itZmfFFa1wO65yWy29Aca3sj"
    "cjooAC3OMJtwL7Jz6EMkPkHb/60dL33cG1DMNrvekotWLoJ/A5yYj7HgnBVw89WB"
    "OBOofXk/bu/dNBf1j/DdSJArfDvtevUTDrJYylKK4JKj8S64taj4Y3gHKp3CHaMr"
    "QIDAQAB"
)


async def _register_device(client, headers):
    r = await client.post(
        "/api/v1/devices",
        headers=headers,
        json={"device_name": "Test", "public_key": VALID_SPKI},
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.mark.anyio
async def test_send_dm_with_shared_post(client):
    """Sending a DM with shared_post_id stores the reference and enriches it on read."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    alice_dev = await _register_device(client, alice_h)
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
            "device_keys": [{"device_id": alice_dev, "encrypted_key": "wrapped"}],
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

    alice_dev = await _register_device(client, alice_h)
    bob_me = await client.get("/api/v1/users/me", headers=bob_h)
    bob_id = bob_me.json()["id"]

    r = await client.post(
        "/api/v1/messages",
        headers=alice_h,
        json={
            "recipient_id": bob_id,
            "ciphertext": "Check this out!",
            "device_keys": [{"device_id": alice_dev, "encrypted_key": "wrapped"}],
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

    alice_dev = await _register_device(client, alice_h)
    bob_me = await client.get("/api/v1/users/me", headers=bob_h)
    bob_id = bob_me.json()["id"]

    r = await client.post(
        "/api/v1/messages",
        headers=alice_h,
        json={
            "recipient_id": bob_id,
            "ciphertext": "Just a normal message",
            "device_keys": [{"device_id": alice_dev, "encrypted_key": "wrapped"}],
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
