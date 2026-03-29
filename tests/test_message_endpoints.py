"""Tests for message endpoints: multi-device keys, cursor pagination, inbox preview, single fetch, deletion."""

import pytest

from tests.conftest import setup_user

# Valid RSA-2048 SPKI keys for test devices
VALID_SPKI_1 = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAv06L2BLDCJpXoKQzty0i"
    "Ae9iSGYUFTQTiO0nplL1tQ/NOqwB3d5F16hCCJY3bkvs5rLEBO0M4dQLlgXt1iOt"
    "8pVMiZGUBDiU7EUxVfgiIl9OKSWCNMaFz46uUiIQpWVXAHT1RkXAuVO63aibvmA1"
    "IaHMZ6gOePlzqVyCqFPpHbb+ktDAD3s5GTCQHYTL3itZmfFFa1wO65yWy29Aca3sj"
    "cjooAC3OMJtwL7Jz6EMkPkHb/60dL33cG1DMNrvekotWLoJ/A5yYj7HgnBVw89WB"
    "OBOofXk/bu/dNBf1j/DdSJArfDvtevUTDrJYylKK4JKj8S64taj4Y3gHKp3CHaMr"
    "QIDAQAB"
)

VALID_SPKI_2 = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxzunqiwDjZkxAEmuCzLT"
    "WPL6SoKsW74A6VEfdzIVdjU16iRP53O9vPJrwcsrIi2JZagVmudZ1mvl1Em2RxFN"
    "qg6jq8WCBJI4pyMgrt112KjGbYmav60ad50UR0YPt62coOPQV4J3335itOLGI58Sg"
    "hSe15liRICFaDOake7KXTjheAR2/4goSOqS1gQ6ynAg+plwQWDdLYuU3cfZ+CbA8"
    "DvexpvbQ3/Y93F+UaraTDS1IEF4fX/8ocvkDNGf74kQ4AYDz8f1kqF1lZppANpSf"
    "KvbnIQppmzULPKtqa+LhsJyXAPGgsx4QO9Dsi0+SUaf/MVjxUeb2gdiB6AAZfH74"
    "wIDAQAB"
)


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _register_device(client, headers, public_key=VALID_SPKI_1, name="Device"):
    r = await client.post(
        "/api/v1/devices",
        headers=headers,
        json={"device_name": name, "public_key": public_key},
    )
    assert r.status_code == 201
    return r.json()


async def _get_user_id(client, headers):
    r = await client.get("/api/v1/users/me", headers=headers)
    return r.json()["id"]


async def _send_dm(
    client, sender_headers, recipient_id, text="hello", device_keys=None
):
    """Send a DM and return the response JSON."""
    payload = {
        "recipient_id": recipient_id,
        "ciphertext": text,
        "device_keys": device_keys or [],
    }
    r = await client.post("/api/v1/messages", headers=sender_headers, json=payload)
    assert r.status_code == 201
    return r.json()


async def _setup_with_devices(client, username, public_key=VALID_SPKI_1):
    """Register a user + device, return (headers, user_id, device_id)."""
    h = await setup_user(client, username)
    uid = await _get_user_id(client, h)
    dev = await _register_device(client, h, public_key=public_key)
    return h, uid, dev["id"]


# ── Multi-device message send ───────────────────────────────────────────────


@pytest.mark.anyio
async def test_send_with_device_keys(client):
    """Messages sent with device_keys store per-device wrapped keys."""
    alice_h, alice_id, alice_dev = await _setup_with_devices(
        client, "alice", VALID_SPKI_1
    )
    bob_h, bob_id, bob_dev = await _setup_with_devices(client, "bob", VALID_SPKI_2)

    dk = [
        {"device_id": alice_dev, "encrypted_key": "wrapped_for_alice"},
        {"device_id": bob_dev, "encrypted_key": "wrapped_for_bob"},
    ]
    msg = await _send_dm(client, alice_h, bob_id, "hi bob", device_keys=dk)
    assert msg["device_keys"] == dk


@pytest.mark.anyio
async def test_send_with_invalid_device_id(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    r = await client.post(
        "/api/v1/messages",
        headers=alice_h,
        json={
            "recipient_id": bob_id,
            "ciphertext": "test",
            "device_keys": [{"device_id": 99999, "encrypted_key": "x"}],
        },
    )
    assert r.status_code == 400


@pytest.mark.anyio
async def test_conversation_returns_device_key_for_requesting_device(client):
    """get_conversation returns only the requesting device's key."""
    alice_h, alice_id, alice_dev = await _setup_with_devices(
        client, "alice", VALID_SPKI_1
    )
    bob_h, bob_id, bob_dev = await _setup_with_devices(client, "bob", VALID_SPKI_2)

    dk = [
        {"device_id": alice_dev, "encrypted_key": "wrapped_alice"},
        {"device_id": bob_dev, "encrypted_key": "wrapped_bob"},
    ]
    await _send_dm(client, alice_h, bob_id, "multi-device msg", device_keys=dk)

    # Bob fetches with his device_id → should get only his key
    r = await client.get(
        f"/api/v1/messages/{alice_id}?device_id={bob_dev}", headers=bob_h
    )
    assert r.status_code == 200
    msgs = r.json()
    assert len(msgs) == 1
    assert len(msgs[0]["device_keys"]) == 1
    assert msgs[0]["device_keys"][0]["device_id"] == bob_dev
    assert msgs[0]["device_keys"][0]["encrypted_key"] == "wrapped_bob"


@pytest.mark.anyio
async def test_single_message_returns_device_key(client):
    alice_h, alice_id, alice_dev = await _setup_with_devices(
        client, "alice", VALID_SPKI_1
    )
    bob_h, bob_id, bob_dev = await _setup_with_devices(client, "bob", VALID_SPKI_2)

    dk = [
        {"device_id": alice_dev, "encrypted_key": "alice_key"},
        {"device_id": bob_dev, "encrypted_key": "bob_key"},
    ]
    msg = await _send_dm(client, alice_h, bob_id, "single fetch test", device_keys=dk)

    r = await client.get(
        f"/api/v1/messages/single/{msg['id']}?device_id={bob_dev}", headers=bob_h
    )
    assert r.status_code == 200
    assert len(r.json()["device_keys"]) == 1
    assert r.json()["device_keys"][0]["encrypted_key"] == "bob_key"


@pytest.mark.anyio
async def test_inbox_includes_device_key_for_preview(client):
    alice_h, alice_id, alice_dev = await _setup_with_devices(
        client, "alice", VALID_SPKI_1
    )
    bob_h, bob_id, bob_dev = await _setup_with_devices(client, "bob", VALID_SPKI_2)

    dk = [
        {"device_id": alice_dev, "encrypted_key": "alice_preview_key"},
        {"device_id": bob_dev, "encrypted_key": "bob_preview_key"},
    ]
    await _send_dm(client, alice_h, bob_id, "preview", device_keys=dk)

    r = await client.get(f"/api/v1/messages?device_id={bob_dev}", headers=bob_h)
    assert r.status_code == 200
    convos = r.json()
    assert len(convos) == 1
    assert convos[0]["last_message_device_key"] == "bob_preview_key"
    assert convos[0]["last_message_ciphertext"] == "preview"


# ── Cursor pagination ────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_cursor_pagination_basic(client):
    """before_id returns only messages with id < cursor."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msgs = []
    for i in range(5):
        m = await _send_dm(client, alice_h, bob_id, f"msg-{i}")
        msgs.append(m)

    alice_id = await _get_user_id(client, alice_h)

    # Full page (no cursor)
    r = await client.get(f"/api/v1/messages/{alice_id}", headers=bob_h)
    assert r.status_code == 200
    assert len(r.json()) == 5

    # With cursor = id of msg-2 → should get msg-0 and msg-1 only
    cursor = msgs[2]["id"]
    r = await client.get(
        f"/api/v1/messages/{alice_id}?before_id={cursor}", headers=bob_h
    )
    assert r.status_code == 200
    result = r.json()
    assert len(result) == 2
    assert all(m["id"] < cursor for m in result)


# ── Single message fetch ─────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_get_single_message(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "hello bob")

    r = await client.get(f"/api/v1/messages/single/{msg['id']}", headers=alice_h)
    assert r.status_code == 200
    assert r.json()["ciphertext"] == "hello bob"

    r = await client.get(f"/api/v1/messages/single/{msg['id']}", headers=bob_h)
    assert r.status_code == 200


@pytest.mark.anyio
async def test_get_single_message_forbidden(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    carol_h = await setup_user(client, "carol")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "private")

    r = await client.get(f"/api/v1/messages/single/{msg['id']}", headers=carol_h)
    assert r.status_code == 403


@pytest.mark.anyio
async def test_get_single_message_not_found(client):
    alice_h = await setup_user(client, "alice")
    r = await client.get("/api/v1/messages/single/99999", headers=alice_h)
    assert r.status_code == 404


# ── Message deletion ─────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_delete_message_success(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "oops")

    r = await client.delete(f"/api/v1/messages/{msg['id']}", headers=alice_h)
    assert r.status_code == 204

    alice_id = await _get_user_id(client, alice_h)
    r = await client.get(f"/api/v1/messages/{alice_id}", headers=bob_h)
    msgs = r.json()
    assert len(msgs) == 1
    assert msgs[0]["is_deleted"] is True
    assert msgs[0]["ciphertext"] == ""


@pytest.mark.anyio
async def test_delete_message_not_sender(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "mine")

    r = await client.delete(f"/api/v1/messages/{msg['id']}", headers=bob_h)
    assert r.status_code == 403


@pytest.mark.anyio
async def test_delete_message_already_deleted(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "gone")
    await client.delete(f"/api/v1/messages/{msg['id']}", headers=alice_h)
    r = await client.delete(f"/api/v1/messages/{msg['id']}", headers=alice_h)
    assert r.status_code == 400


@pytest.mark.anyio
async def test_delete_message_not_found(client):
    alice_h = await setup_user(client, "alice")
    r = await client.delete("/api/v1/messages/99999", headers=alice_h)
    assert r.status_code == 404


@pytest.mark.anyio
async def test_delete_message_too_old(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "old message")

    from datetime import datetime, timedelta, timezone

    from sqlalchemy import update as sa_update

    from app.models.message import Message
    from tests.conftest import get_test_db

    async for db in get_test_db():
        await db.execute(
            sa_update(Message)
            .where(Message.id == msg["id"])
            .values(created_at=datetime.now(timezone.utc) - timedelta(hours=2))
        )
        await db.commit()

    r = await client.delete(f"/api/v1/messages/{msg['id']}", headers=alice_h)
    assert r.status_code == 403
    assert "1 hour" in r.json()["detail"]


@pytest.mark.anyio
async def test_deleted_single_message_clears_ciphertext(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "will be deleted")
    await client.delete(f"/api/v1/messages/{msg['id']}", headers=alice_h)

    r = await client.get(f"/api/v1/messages/single/{msg['id']}", headers=bob_h)
    assert r.status_code == 200
    assert r.json()["is_deleted"] is True
    assert r.json()["ciphertext"] == ""


@pytest.mark.anyio
async def test_inbox_deleted_message_clears_preview(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "secret")
    await client.delete(f"/api/v1/messages/{msg['id']}", headers=alice_h)

    r = await client.get("/api/v1/messages", headers=alice_h)
    convos = r.json()
    c = convos[0]
    assert c["last_message_is_deleted"] is True
    assert c["last_message_ciphertext"] is None


# ── WS payload includes message_id ───────────────────────────────────────────


@pytest.mark.anyio
async def test_send_message_ws_payload_includes_message_id(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    import app.api.v1.messages as msg_module

    captured = []
    original = msg_module.publish_to_user

    async def mock_publish(user_id, event_type, data):
        captured.append({"user_id": user_id, "type": event_type, "data": data})

    msg_module.publish_to_user = mock_publish
    try:
        msg = await _send_dm(client, alice_h, bob_id, "check payload")
        assert len(captured) == 1
        assert captured[0]["data"]["message_id"] == msg["id"]
        assert captured[0]["data"]["sender_id"] is not None
    finally:
        msg_module.publish_to_user = original
