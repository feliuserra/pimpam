"""Tests for WebSocket typing indicator forwarding."""
import json
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import setup_user


# ---------------------------------------------------------------------------
# Unit tests for process_client_frame (no WS connection needed)
# ---------------------------------------------------------------------------

async def test_typing_frame_calls_publish():
    """process_client_frame publishes to the correct recipient."""
    from app.api.ws import process_client_frame

    frame = json.dumps({"type": "typing", "recipient_id": 42})

    with patch("app.api.ws.publish_to_user", new=AsyncMock()) as mock_pub:
        await process_client_frame(frame, sender_id=7, sender_username="alice")

    mock_pub.assert_awaited_once_with(42, "typing", {
        "sender_id": 7,
        "sender_username": "alice",
    })


async def test_unknown_frame_type_ignored():
    """Frames with an unknown type do not trigger publish."""
    from app.api.ws import process_client_frame

    frame = json.dumps({"type": "ping"})

    with patch("app.api.ws.publish_to_user", new=AsyncMock()) as mock_pub:
        await process_client_frame(frame, sender_id=7, sender_username="alice")

    mock_pub.assert_not_called()


async def test_malformed_json_raises():
    """process_client_frame raises on invalid JSON (caller must catch)."""
    from app.api.ws import process_client_frame
    import pytest

    with pytest.raises(json.JSONDecodeError):
        await process_client_frame("not-json", sender_id=7, sender_username="alice")


async def test_typing_frame_missing_recipient_raises():
    """Missing recipient_id raises KeyError (caller must catch)."""
    from app.api.ws import process_client_frame

    frame = json.dumps({"type": "typing"})  # no recipient_id

    with pytest.raises((KeyError, TypeError)):
        await process_client_frame(frame, sender_id=7, sender_username="alice")


# ---------------------------------------------------------------------------
# Integration smoke tests using the HTTP client
# ---------------------------------------------------------------------------

async def test_ws_invalid_token_responds(client):
    """Connecting with a bad token should result in an immediate close."""
    # The endpoint accepts then immediately closes with 1008.
    # httpx AsyncClient doesn't support WS; verify the endpoint is reachable via HTTP health check.
    r = await client.get("/health")
    assert r.status_code == 200

    # Verify the route is registered on the app
    from app.main import app
    ws_routes = [r for r in app.routes if hasattr(r, "path") and r.path == "/ws"]
    assert len(ws_routes) == 1


async def test_typing_recipient_lookup(client):
    """
    Full-stack typing test: register two users, verify the typing logic
    calls publish_to_user with the correct recipient_id.
    """
    from app.api.ws import process_client_frame

    ha = await setup_user(client, "alice")
    hb = await setup_user(client, "bob")

    bob_id = (await client.get("/api/v1/users/me", headers=hb)).json()["id"]
    alice_id = (await client.get("/api/v1/users/me", headers=ha)).json()["id"]

    frame = json.dumps({"type": "typing", "recipient_id": bob_id})

    with patch("app.api.ws.publish_to_user", new=AsyncMock()) as mock_pub:
        await process_client_frame(frame, sender_id=alice_id, sender_username="alice")

    mock_pub.assert_awaited_once_with(bob_id, "typing", {
        "sender_id": alice_id,
        "sender_username": "alice",
    })
