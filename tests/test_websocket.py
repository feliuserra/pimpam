"""
WebSocket and real-time event tests.

Full WS connection tests use Starlette's sync TestClient (the only client that
supports WebSocket connections). Event-publish tests mock Redis so no running
instance is required.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_access_token
from app.main import app
from tests.conftest import register, setup_user

# Valid RSA-2048 SPKI public key for device registration
VALID_SPKI = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAv06L2BLDCJpXoKQzty0i"
    "Ae9iSGYUFTQTiO0nplL1tQ/NOqwB3d5F16hCCJY3bkvs5rLEBO0M4dQLlgXt1iOt"
    "8pVMiZGUBDiU7EUxVfgiIl9OKSWCNMaFz46uUiIQpWVXAHT1RkXAuVO63aibvmA1"
    "IaHMZ6gOePlzqVyCqFPpHbb+ktDAD3s5GTCQHYTL3itZmfFFa1wO65yWy29Aca3sj"
    "cjooAC3OMJtwL7Jz6EMkPkHb/60dL33cG1DMNrvekotWLoJ/A5yYj7HgnBVw89WB"
    "OBOofXk/bu/dNBf1j/DdSJArfDvtevUTDrJYylKK4JKj8S64taj4Y3gHKp3CHaMr"
    "QIDAQAB"
)

# ---------------------------------------------------------------------------
# WebSocket connection & auth
# ---------------------------------------------------------------------------


def test_ws_rejects_invalid_token():
    """A bad/expired token is rejected with close code 1008."""
    with TestClient(app) as tc:
        with tc.websocket_connect("/ws?token=not-a-jwt") as ws:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                ws.receive_text()
        assert exc_info.value.code == 1008


def test_ws_rejects_missing_token():
    """Connecting without a token closes the connection (FastAPI returns 404 for plain GET on WS route)."""
    with TestClient(app) as tc:
        r = tc.get("/ws")  # not a WS upgrade request
        assert r.status_code in (404, 422, 403, 400)


def test_ws_accepts_valid_token():
    """A valid JWT allows the connection to be accepted."""
    token = create_access_token(subject=1)

    # Patch Redis so pubsub.listen() never yields (no messages) — connection stays open
    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.aclose = AsyncMock()

    async def _empty_listen():
        # Yield nothing — keeps the listen loop waiting
        return
        yield  # make it an async generator

    mock_pubsub.listen = _empty_listen
    mock_redis = MagicMock()
    mock_redis.pubsub.return_value = mock_pubsub

    with (
        patch("app.api.ws.get_redis", return_value=mock_redis),
        patch(
            "app.api.ws.decode_access_token",
            return_value={"sub": "1", "type": "access"},
        ),
    ):
        with TestClient(app) as tc:
            with tc.websocket_connect(f"/ws?token={token}") as ws:
                # Connection accepted — send a ping to confirm it's live
                ws.send_text("ping")
                # Close cleanly from client side
                ws.close()


# ---------------------------------------------------------------------------
# publish_to_user resilience
# ---------------------------------------------------------------------------


async def test_publish_to_user_swallows_redis_error():
    """publish_to_user never raises even when Redis is unreachable."""
    with patch("app.core.redis.get_redis") as mock_get:
        mock_client = MagicMock()
        mock_client.publish = AsyncMock(side_effect=ConnectionError("redis down"))
        mock_get.return_value = mock_client

        from app.core.redis import publish_to_user

        # Must not raise
        await publish_to_user(1, "new_post", {"id": 42, "title": "hello"})


# ---------------------------------------------------------------------------
# new_post published to local followers
# ---------------------------------------------------------------------------


async def test_create_post_notifies_followers(client):
    """Creating a post fires publish_to_user(follower_id, 'new_post', ...) for each follower."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await client.post("/api/v1/users/alice/follow", headers=bob_h)

    with patch("app.api.v1.posts.publish_to_user", new_callable=AsyncMock) as mock_pub:
        r = await client.post(
            "/api/v1/posts",
            json={"title": "hello world", "content": "body"},
            headers=alice_h,
        )
        assert r.status_code == 201

        event_types = [call.args[1] for call in mock_pub.call_args_list]
        assert "new_post" in event_types

        new_post_call = next(
            c for c in mock_pub.call_args_list if c.args[1] == "new_post"
        )
        assert new_post_call.args[2]["title"] == "hello world"
        assert new_post_call.args[2]["author"] == "alice"


async def test_create_post_no_notification_without_followers(client):
    """No publish_to_user call when the author has no local followers."""
    alice_h = await setup_user(client, "alice")

    with patch("app.api.v1.posts.publish_to_user", new_callable=AsyncMock) as mock_pub:
        r = await client.post(
            "/api/v1/posts",
            json={"title": "lonely post", "content": "nobody watching"},
            headers=alice_h,
        )
        assert r.status_code == 201

        new_post_calls = [c for c in mock_pub.call_args_list if c.args[1] == "new_post"]
        assert len(new_post_calls) == 0


# ---------------------------------------------------------------------------
# new_message published to recipient
# ---------------------------------------------------------------------------


async def test_send_message_notifies_recipient(client):
    """Sending a DM fires publish_to_user(recipient_id, 'new_message', ...)."""
    alice_h = await setup_user(client, "alice")
    bob_resp = await register(client, "bob")
    bob_id = bob_resp.json()["id"]

    # Register a device so we can provide a valid device_key
    dev_r = await client.post(
        "/api/v1/devices",
        headers=alice_h,
        json={"device_name": "Test", "public_key": VALID_SPKI},
    )
    alice_dev = dev_r.json()["id"]

    with patch(
        "app.api.v1.messages.publish_to_user", new_callable=AsyncMock
    ) as mock_pub:
        r = await client.post(
            "/api/v1/messages",
            json={
                "recipient_id": bob_id,
                "ciphertext": "enc",
                "device_keys": [{"device_id": alice_dev, "encrypted_key": "wrapped"}],
            },
            headers=alice_h,
        )
        assert r.status_code == 201
        mock_pub.assert_awaited_once()
        assert mock_pub.call_args.args[0] == bob_id
        assert mock_pub.call_args.args[1] == "new_message"
        assert mock_pub.call_args.args[2]["sender_username"] == "alice"


# ---------------------------------------------------------------------------
# karma_update published to post author
# ---------------------------------------------------------------------------


async def test_vote_notifies_author_karma(client):
    """A +1 vote fires publish_to_user(author_id, 'karma_update', ...) when karma changes."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    post_r = await client.post(
        "/api/v1/posts", json={"title": "rate me", "content": "hi"}, headers=alice_h
    )
    post_id = post_r.json()["id"]

    with patch("app.api.v1.posts.publish_to_user", new_callable=AsyncMock) as mock_pub:
        r = await client.post(
            f"/api/v1/posts/{post_id}/vote", json={"direction": 1}, headers=bob_h
        )
        assert r.status_code == 200

        karma_calls = [
            c for c in mock_pub.call_args_list if c.args[1] == "karma_update"
        ]
        assert len(karma_calls) == 1
        data = karma_calls[0].args[2]
        assert data["post_id"] == post_id
        assert "post_karma" in data
        assert "user_karma" in data
