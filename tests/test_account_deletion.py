"""Tests for account deletion flow."""

from unittest.mock import patch

from tests.conftest import get_test_db


async def setup_verified_user(client, username):
    """Register, verify, and return auth headers."""
    captured = {}

    async def mock_send(to, token):
        captured["token"] = token

    with patch("app.api.v1.auth.send_verification_email", new=mock_send):
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": "testpass123",
            },
        )

    await client.get(f"/api/v1/auth/verify?token={captured['token']}")
    r = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": "testpass123"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Schedule deletion
# ---------------------------------------------------------------------------


async def test_schedule_deletion_requires_correct_password(client):
    ha = await setup_verified_user(client, "alice")
    r = await client.post(
        "/api/v1/users/me/delete", json={"password": "wrongpass"}, headers=ha
    )
    assert r.status_code == 401


async def test_schedule_deletion_returns_202(client):
    ha = await setup_verified_user(client, "alice")
    r = await client.post(
        "/api/v1/users/me/delete", json={"password": "testpass123"}, headers=ha
    )
    assert r.status_code == 202


async def test_schedule_deletion_sets_scheduled_at(client):
    ha = await setup_verified_user(client, "alice")
    await client.post(
        "/api/v1/users/me/delete", json={"password": "testpass123"}, headers=ha
    )

    profile = (await client.get("/api/v1/users/me", headers=ha)).json()
    assert profile["deletion_scheduled_at"] is not None


async def test_schedule_deletion_twice_returns_409(client):
    ha = await setup_verified_user(client, "alice")
    await client.post(
        "/api/v1/users/me/delete", json={"password": "testpass123"}, headers=ha
    )
    r = await client.post(
        "/api/v1/users/me/delete", json={"password": "testpass123"}, headers=ha
    )
    assert r.status_code == 409


async def test_user_can_still_use_platform_during_grace(client):
    ha = await setup_verified_user(client, "alice")
    await client.post(
        "/api/v1/users/me/delete", json={"password": "testpass123"}, headers=ha
    )

    # Should still be able to read their own profile
    r = await client.get("/api/v1/users/me", headers=ha)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Cancel deletion
# ---------------------------------------------------------------------------


async def test_cancel_deletion(client):
    ha = await setup_verified_user(client, "alice")
    await client.post(
        "/api/v1/users/me/delete", json={"password": "testpass123"}, headers=ha
    )

    r = await client.post("/api/v1/users/me/delete/cancel", headers=ha)
    assert r.status_code == 200

    profile = (await client.get("/api/v1/users/me", headers=ha)).json()
    assert profile["deletion_scheduled_at"] is None


async def test_cancel_when_not_scheduled_returns_400(client):
    ha = await setup_verified_user(client, "alice")
    r = await client.post("/api/v1/users/me/delete/cancel", headers=ha)
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Execute deletion (direct CRUD call)
# ---------------------------------------------------------------------------


async def test_execute_deletion_removes_user(client):
    from app.crud.account_deletion import execute_deletion

    ha = await setup_verified_user(client, "alice")

    # Get alice's user_id
    profile = (await client.get("/api/v1/users/me", headers=ha)).json()
    user_id = profile["id"]

    async for db in get_test_db():
        await execute_deletion(db, user_id)

    # alice's profile should now 404
    r = await client.get("/api/v1/users/alice")
    assert r.status_code == 404


async def test_execute_deletion_anonymizes_posts(client):
    from app.crud.account_deletion import execute_deletion

    ha = await setup_verified_user(client, "alice")
    profile = (await client.get("/api/v1/users/me", headers=ha)).json()
    user_id = profile["id"]

    # alice creates a post
    post = (
        await client.post(
            "/api/v1/posts", json={"title": "Hello", "content": "World"}, headers=ha
        )
    ).json()

    async for db in get_test_db():
        await execute_deletion(db, user_id)

    # Post should still exist but with null author_id
    r = await client.get(f"/api/v1/posts/{post['id']}")
    assert r.status_code == 200
    assert r.json()["author_id"] is None


async def test_execute_deletion_removes_received_messages(client):
    from app.crud.account_deletion import execute_deletion
    from app.models.message import Message
    from sqlalchemy import select

    ha = await setup_verified_user(client, "alice")
    hb = await setup_verified_user(client, "bob")

    alice_id = (await client.get("/api/v1/users/me", headers=ha)).json()["id"]

    # Bob sends alice a message
    await client.post(
        "/api/v1/messages",
        json={
            "recipient_id": alice_id,
            "ciphertext": "encrypted",
            "device_keys": [],
        },
        headers=hb,
    )

    # Delete alice
    async for db in get_test_db():
        await execute_deletion(db, alice_id)

    # Message should be deleted (alice was recipient)
    async for db in get_test_db():
        result = await db.execute(
            select(Message).where(Message.recipient_id == alice_id)
        )
        assert result.scalar_one_or_none() is None


async def test_execute_deletion_anonymizes_sent_messages(client):
    from app.crud.account_deletion import execute_deletion
    from app.models.message import Message
    from sqlalchemy import select

    ha = await setup_verified_user(client, "alice")
    hb = await setup_verified_user(client, "bob")

    alice_id = (await client.get("/api/v1/users/me", headers=ha)).json()["id"]
    bob_id = (await client.get("/api/v1/users/me", headers=hb)).json()["id"]

    # Alice sends bob a message
    await client.post(
        "/api/v1/messages",
        json={
            "recipient_id": bob_id,
            "ciphertext": "encrypted",
            "device_keys": [],
        },
        headers=ha,
    )

    # Delete alice
    async for db in get_test_db():
        await execute_deletion(db, alice_id)

    # Message to bob should still exist but sender_id is null
    async for db in get_test_db():
        result = await db.execute(select(Message).where(Message.recipient_id == bob_id))
        msg = result.scalar_one_or_none()
        assert msg is not None
        assert msg.sender_id is None
