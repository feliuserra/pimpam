"""Tests for message endpoints: cursor pagination, inbox preview, single fetch, deletion."""

import pytest

from tests.conftest import setup_user

# ── helpers ──────────────────────────────────────────────────────────────────


async def _send_dm(client, sender_headers, recipient_id, text="hello"):
    """Send a DM and return the response JSON."""
    r = await client.post(
        "/api/v1/messages",
        headers=sender_headers,
        json={
            "recipient_id": recipient_id,
            "ciphertext": text,
            "encrypted_key": "fakekey",
            "sender_encrypted_key": "sender_fakekey",
        },
    )
    assert r.status_code == 201
    return r.json()


async def _get_user_id(client, headers):
    r = await client.get("/api/v1/users/me", headers=headers)
    return r.json()["id"]


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


# ── Inbox preview ────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_inbox_includes_last_message_fields(client):
    """Inbox entries should include encrypted last message data for preview."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "preview text")

    r = await client.get("/api/v1/messages", headers=alice_h)
    assert r.status_code == 200
    convos = r.json()
    assert len(convos) == 1
    c = convos[0]
    assert c["last_message_id"] == msg["id"]
    assert c["last_message_ciphertext"] == "preview text"
    assert c["last_message_encrypted_key"] == "fakekey"
    assert c["last_message_sender_encrypted_key"] == "sender_fakekey"
    assert c["last_message_is_deleted"] is False


@pytest.mark.anyio
async def test_inbox_deleted_message_clears_preview(client):
    """If the last message is deleted, inbox should clear ciphertext."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "secret")

    # Delete the message
    r = await client.delete(f"/api/v1/messages/{msg['id']}", headers=alice_h)
    assert r.status_code == 204

    r = await client.get("/api/v1/messages", headers=alice_h)
    convos = r.json()
    c = convos[0]
    assert c["last_message_is_deleted"] is True
    assert c["last_message_ciphertext"] is None
    assert c["last_message_encrypted_key"] is None


# ── Single message fetch ─────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_get_single_message(client):
    """GET /messages/single/{id} returns the message for sender or recipient."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "hello bob")

    # Sender can fetch
    r = await client.get(f"/api/v1/messages/single/{msg['id']}", headers=alice_h)
    assert r.status_code == 200
    assert r.json()["ciphertext"] == "hello bob"

    # Recipient can fetch
    r = await client.get(f"/api/v1/messages/single/{msg['id']}", headers=bob_h)
    assert r.status_code == 200
    assert r.json()["ciphertext"] == "hello bob"


@pytest.mark.anyio
async def test_get_single_message_forbidden(client):
    """A third user cannot access someone else's message."""
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
    """Sender can delete their own message within 1 hour."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "oops")

    r = await client.delete(f"/api/v1/messages/{msg['id']}", headers=alice_h)
    assert r.status_code == 204

    # Message should appear as tombstone in conversation
    alice_id = await _get_user_id(client, alice_h)
    r = await client.get(f"/api/v1/messages/{alice_id}", headers=bob_h)
    msgs = r.json()
    assert len(msgs) == 1
    assert msgs[0]["is_deleted"] is True
    assert msgs[0]["ciphertext"] == ""


@pytest.mark.anyio
async def test_delete_message_not_sender(client):
    """Recipient cannot delete the sender's message."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "mine")

    r = await client.delete(f"/api/v1/messages/{msg['id']}", headers=bob_h)
    assert r.status_code == 403
    assert "sender" in r.json()["detail"].lower()


@pytest.mark.anyio
async def test_delete_message_already_deleted(client):
    """Deleting an already-deleted message returns 400."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "gone")

    r = await client.delete(f"/api/v1/messages/{msg['id']}", headers=alice_h)
    assert r.status_code == 204

    r = await client.delete(f"/api/v1/messages/{msg['id']}", headers=alice_h)
    assert r.status_code == 400


@pytest.mark.anyio
async def test_delete_message_not_found(client):
    alice_h = await setup_user(client, "alice")
    r = await client.delete("/api/v1/messages/99999", headers=alice_h)
    assert r.status_code == 404


@pytest.mark.anyio
async def test_delete_message_too_old(client):
    """Cannot delete a message older than 1 hour."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "old message")

    # Manually age the message in the DB
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
    """GET /messages/single/{id} clears ciphertext for deleted messages."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    msg = await _send_dm(client, alice_h, bob_id, "will be deleted")
    await client.delete(f"/api/v1/messages/{msg['id']}", headers=alice_h)

    r = await client.get(f"/api/v1/messages/single/{msg['id']}", headers=bob_h)
    assert r.status_code == 200
    assert r.json()["is_deleted"] is True
    assert r.json()["ciphertext"] == ""


# ── WS payload includes message_id ───────────────────────────────────────────


@pytest.mark.anyio
async def test_send_message_ws_payload_includes_message_id(client):
    """The new_message WS event should include message_id."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    bob_id = await _get_user_id(client, bob_h)

    # Patch publish_to_user to capture the payload
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
