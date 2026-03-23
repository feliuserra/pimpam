"""
WebSocket real-time event stream.

Connect: ``ws://<host>/ws?token=<access_token>``

Events pushed to the client:
  {"type": "new_post",     "data": {"id": 1, "title": "...", "author": "alice"}}
  {"type": "new_message",  "data": {"sender_id": 2, "sender_username": "bob"}}
  {"type": "karma_update", "data": {"post_id": 1, "post_karma": 5, "user_karma": 12}}

The connection is closed after 60 seconds of client silence. Clients should reconnect
and will receive only events published after reconnection (no catch-up / replay).
"""
import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.redis import get_redis
from app.core.security import decode_token

router = APIRouter(tags=["websocket"])

IDLE_TIMEOUT = 60.0  # seconds before the server closes an idle connection


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """
    Real-time event stream for the authenticated user.
    Authenticate with a valid JWT access token passed as ``?token=``.
    The connection closes after 60 s of inactivity; clients should reconnect.
    """
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        await websocket.accept()
        await websocket.close(code=1008)  # 1008 = Policy Violation
        return

    await websocket.accept()

    channel = f"pimpam:user:{user_id}"
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(channel)

    async def forward_redis_to_ws() -> None:
        """Forward every Redis message on the user's channel to the WebSocket."""
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])

    async def wait_for_client_or_timeout() -> None:
        """
        Consume any frames sent by the client (heartbeat pings are fine).
        Returns when the client disconnects or after IDLE_TIMEOUT seconds of silence.
        """
        try:
            while True:
                await asyncio.wait_for(websocket.receive_text(), timeout=IDLE_TIMEOUT)
        except (asyncio.TimeoutError, WebSocketDisconnect):
            pass

    fwd_task = asyncio.create_task(forward_redis_to_ws())
    idle_task = asyncio.create_task(wait_for_client_or_timeout())

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
