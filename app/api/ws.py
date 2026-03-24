"""
WebSocket real-time event stream.

Connect: ``ws://<host>/ws?token=<access_token>``

Events pushed **to** the client:
  {"type": "new_post",     "data": {"id": 1, "title": "...", "author": "alice"}}
  {"type": "new_message",  "data": {"sender_id": 2, "sender_username": "bob"}}
  {"type": "karma_update", "data": {"post_id": 1, "post_karma": 5, "user_karma": 12}}
  {"type": "typing",       "data": {"sender_id": 2, "sender_username": "bob"}}

Events sent **from** the client:
  {"type": "typing", "recipient_id": <int>}   — forward a typing indicator to the recipient

The connection is closed after 60 seconds of client silence. Clients should reconnect
and will receive only events published after reconnection (no catch-up / replay).
"""
import asyncio
import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.redis import get_redis, publish_to_user
from app.core.security import decode_token

router = APIRouter(tags=["websocket"])

IDLE_TIMEOUT = 60.0  # seconds before the server closes an idle connection


async def process_client_frame(raw: str, sender_id: int, sender_username: str) -> None:
    """
    Parse one text frame from a connected client and act on it.

    Currently handles:
    - ``{"type": "typing", "recipient_id": <int>}`` — forward typing indicator to recipient.

    All other frames are silently ignored.
    Extracted as a module-level function so it can be unit-tested independently.
    """
    msg = json.loads(raw)
    if msg.get("type") == "typing":
        recipient_id = int(msg["recipient_id"])
        await publish_to_user(recipient_id, "typing", {
            "sender_id": sender_id,
            "sender_username": sender_username,
        })


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """
    Real-time event stream for the authenticated user.
    Authenticate with a valid JWT access token passed as ``?token=``.
    The connection closes after 60 s of inactivity; clients should reconnect.

    Clients may also send ``{"type": "typing", "recipient_id": <int>}`` to
    forward a typing indicator to the recipient user in real time.
    """
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        await websocket.accept()
        await websocket.close(code=1008)  # 1008 = Policy Violation
        return

    # Fetch the sender's username once — needed when forwarding typing events.
    username: str = ""
    try:
        from app.crud.user import get_user_by_id
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            user = await get_user_by_id(db, user_id)
            if user:
                username = user.username
    except Exception:
        pass  # username stays empty; typing events will still be forwarded without it

    await websocket.accept()

    channel = f"pimpam:user:{user_id}"
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(channel)

    async def forward_redis_to_ws() -> None:
        """Forward every Redis message on the user's channel to the WebSocket."""
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])

    async def handle_client_messages() -> None:
        """
        Consume and process frames sent by the client.
        Closes after IDLE_TIMEOUT seconds of silence.
        """
        try:
            while True:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=IDLE_TIMEOUT)
                try:
                    await process_client_frame(raw, user_id, username)
                except Exception:
                    pass  # ignore malformed or unknown frames
        except (asyncio.TimeoutError, WebSocketDisconnect):
            pass

    fwd_task = asyncio.create_task(forward_redis_to_ws())
    idle_task = asyncio.create_task(handle_client_messages())

    try:
        await asyncio.wait({fwd_task, idle_task}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        fwd_task.cancel()
        idle_task.cancel()
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        try:
            await websocket.close()
        except Exception:
            pass
