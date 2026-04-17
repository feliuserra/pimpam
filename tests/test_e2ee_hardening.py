"""Tests for E2EE key management hardening."""

import base64
import hashlib

from tests.conftest import setup_user

VALID_KEY = base64.b64encode(b"\x00" * 294).decode()
VALID_KEY_2 = base64.b64encode(b"\x01" * 294).decode()


async def test_set_e2ee_public_key_valid(client):
    """Setting a valid base64 public key populates fingerprint and timestamp."""
    h = await setup_user(client, "alice")

    r = await client.patch(
        "/api/v1/users/me", headers=h, json={"e2ee_public_key": VALID_KEY}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["e2ee_public_key"] == VALID_KEY
    assert data["e2ee_key_fingerprint"] is not None
    assert data["e2ee_key_set_at"] is not None

    expected_fp = hashlib.sha256(base64.b64decode(VALID_KEY)).hexdigest()
    assert data["e2ee_key_fingerprint"] == expected_fp


async def test_set_e2ee_public_key_invalid_base64(client):
    """Non-base64 string is rejected with 422."""
    h = await setup_user(client, "alice")

    r = await client.patch(
        "/api/v1/users/me", headers=h, json={"e2ee_public_key": "not-valid-base64!!!"}
    )
    assert r.status_code == 422


async def test_set_e2ee_public_key_too_short(client):
    """Valid base64 but too few decoded bytes is rejected."""
    h = await setup_user(client, "alice")

    short_key = base64.b64encode(b"\x00" * 10).decode()
    r = await client.patch(
        "/api/v1/users/me", headers=h, json={"e2ee_public_key": short_key}
    )
    assert r.status_code == 422


async def test_e2ee_fingerprint_in_public_profile(client):
    """Fingerprint and timestamp appear on the public user profile."""
    h = await setup_user(client, "alice")

    await client.patch(
        "/api/v1/users/me", headers=h, json={"e2ee_public_key": VALID_KEY}
    )

    r = await client.get("/api/v1/users/alice", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["e2ee_key_fingerprint"] is not None
    assert data["e2ee_key_set_at"] is not None


async def test_e2ee_key_update_changes_fingerprint(client):
    """Updating the key produces a different fingerprint and later timestamp."""
    h = await setup_user(client, "alice")

    r1 = await client.patch(
        "/api/v1/users/me", headers=h, json={"e2ee_public_key": VALID_KEY}
    )
    fp1 = r1.json()["e2ee_key_fingerprint"]
    ts1 = r1.json()["e2ee_key_set_at"]

    r2 = await client.patch(
        "/api/v1/users/me", headers=h, json={"e2ee_public_key": VALID_KEY_2}
    )
    fp2 = r2.json()["e2ee_key_fingerprint"]
    ts2 = r2.json()["e2ee_key_set_at"]

    assert fp1 != fp2
    assert ts2 >= ts1


async def test_send_message_empty_encrypted_key_rejected(client):
    """Sending a message with empty encrypted_key is rejected."""
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")

    bob_id = (await client.get("/api/v1/users/me", headers=hb)).json()["id"]

    r = await client.post(
        "/api/v1/messages",
        headers=ha,
        json={
            "recipient_id": bob_id,
            "ciphertext": "some-ciphertext",
            "encrypted_key": "",
        },
    )
    assert r.status_code == 422


async def test_send_message_nonempty_encrypted_key_works(client):
    """Sending a message with a non-empty encrypted_key still works."""
    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")

    bob_id = (await client.get("/api/v1/users/me", headers=hb)).json()["id"]

    r = await client.post(
        "/api/v1/messages",
        headers=ha,
        json={
            "recipient_id": bob_id,
            "ciphertext": "encrypted-data",
            "encrypted_key": "wrapped-aes-key",
        },
    )
    assert r.status_code == 201
