from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import case, delete, func, or_, select, update

from app.core.dependencies import CurrentUser, DBSession
from app.core.limiter import limiter
from app.core.redis import publish_to_user
from app.crud.user import get_user_by_id
from app.models.message import Message
from app.models.message_device_key import MessageDeviceKey
from app.models.user import User
from app.models.user_device import UserDevice
from app.schemas.message import (
    ConversationSummary,
    DeviceKeyEntry,
    MessagePublic,
    MessageSend,
    SharedPostPreview,
)

router = APIRouter(prefix="/messages", tags=["messages"])


# ── Helpers ──


async def _device_keys_for_messages(
    db,
    message_ids: list[int],
    device_id: int | None,
) -> dict[int, list[DeviceKeyEntry]]:
    """Batch-fetch device keys for a set of messages, filtered to one device."""
    if not message_ids or device_id is None:
        return {}
    result = await db.execute(
        select(MessageDeviceKey).where(
            MessageDeviceKey.message_id.in_(message_ids),
            MessageDeviceKey.device_id == device_id,
        )
    )
    keys_by_msg: dict[int, list[DeviceKeyEntry]] = {}
    for mdk in result.scalars():
        keys_by_msg.setdefault(mdk.message_id, []).append(
            DeviceKeyEntry(device_id=mdk.device_id, encrypted_key=mdk.encrypted_key)
        )
    return keys_by_msg


async def _enrich_shared_posts(
    db, messages: list[Message]
) -> dict[int, SharedPostPreview]:
    """Batch-fetch shared post previews for messages that reference a post."""
    shared_ids = [m.shared_post_id for m in messages if m.shared_post_id]
    if not shared_ids:
        return {}

    from app.models.post import Post

    rows = await db.execute(select(Post).where(Post.id.in_(shared_ids)))
    posts = list(rows.scalars().all())

    # Batch-fetch author data
    author_ids = {p.author_id for p in posts if p.author_id}
    authors: dict[int, tuple[str | None, str | None]] = {}
    if author_ids:
        a_rows = await db.execute(
            select(User.id, User.username, User.avatar_url).where(
                User.id.in_(author_ids)
            )
        )
        for r in a_rows:
            authors[r.id] = (r.username, r.avatar_url)

    # Batch-fetch community names
    community_ids = {p.community_id for p in posts if p.community_id}
    communities: dict[int, str] = {}
    if community_ids:
        from app.models.community import Community

        c_rows = await db.execute(
            select(Community.id, Community.name).where(Community.id.in_(community_ids))
        )
        for r in c_rows:
            communities[r.id] = r.name

    from app.core.media_urls import resolve_urls as _resolve_urls

    _img_keys = [p.image_url for p in posts]
    _avatar_keys = [authors.get(p.author_id, (None, None))[1] for p in posts]
    _resolved = await _resolve_urls(_img_keys + _avatar_keys)
    _resolved_imgs = _resolved[: len(posts)]
    _resolved_avs = _resolved[len(posts) :]

    previews: dict[int, SharedPostPreview] = {}
    for idx, p in enumerate(posts):
        if p.is_removed:
            continue
        author_data = authors.get(p.author_id, (None, None))
        previews[p.id] = SharedPostPreview(
            id=p.id,
            title=p.title,
            content=(p.content[:200] + "...")
            if p.content and len(p.content) > 200
            else p.content,
            image_url=_resolved_imgs[idx],
            author_username=author_data[0],
            author_avatar_url=_resolved_avs[idx],
            community_name=communities.get(p.community_id) if p.community_id else None,
            karma=p.karma,
        )
    return previews


def _message_to_public(
    msg: Message,
    device_keys: list[DeviceKeyEntry] | None = None,
    shared_post: SharedPostPreview | None = None,
) -> MessagePublic:
    """Convert a Message ORM object to a MessagePublic schema."""
    pub = MessagePublic(
        id=msg.id,
        sender_id=msg.sender_id,
        recipient_id=msg.recipient_id,
        ciphertext="" if msg.is_deleted else msg.ciphertext,
        device_keys=device_keys or [],
        shared_post_id=msg.shared_post_id,
        shared_post=shared_post,
        is_read=msg.is_read,
        is_deleted=msg.is_deleted,
        created_at=msg.created_at,
    )
    return pub


# ── Endpoints ──


@router.post("", response_model=MessagePublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def send_message(
    request: Request, data: MessageSend, current_user: CurrentUser, db: DBSession
):
    """
    Send an E2EE message. The server stores only ciphertext.
    Encryption and per-device key wrapping must be done client-side.
    """
    if data.recipient_id == current_user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cannot message yourself"
        )

    recipient = await get_user_by_id(db, data.recipient_id)
    if recipient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Recipient not found")

    from app.crud.block import is_blocked_either_direction

    if await is_blocked_either_direction(db, current_user.id, data.recipient_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Cannot message this user"
        )

    # Validate device_keys — each device must belong to sender or recipient
    if data.device_keys:
        device_ids = [dk.device_id for dk in data.device_keys]
        result = await db.execute(
            select(UserDevice.id, UserDevice.user_id).where(
                UserDevice.id.in_(device_ids),
                UserDevice.is_active == True,  # noqa: E712
            )
        )
        valid_devices = {row.id: row.user_id for row in result.all()}
        for dk in data.device_keys:
            if dk.device_id not in valid_devices:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=f"Device {dk.device_id} not found or not active",
                )
            owner = valid_devices[dk.device_id]
            if owner != current_user.id and owner != data.recipient_id:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=f"Device {dk.device_id} does not belong to sender or recipient",
                )

    # Validate shared post if provided
    shared_post_id = None
    if data.shared_post_id is not None:
        from app.crud.post import get_post

        post = await get_post(db, data.shared_post_id)
        if post is None or post.is_removed:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Shared post not found"
            )
        shared_post_id = post.id

    message = Message(
        sender_id=current_user.id,
        recipient_id=data.recipient_id,
        ciphertext=data.ciphertext,
        shared_post_id=shared_post_id,
    )
    db.add(message)
    await db.flush()  # get message.id

    # Create per-device key rows
    for dk in data.device_keys:
        db.add(
            MessageDeviceKey(
                message_id=message.id,
                device_id=dk.device_id,
                encrypted_key=dk.encrypted_key,
            )
        )

    await db.commit()
    await db.refresh(message)

    await publish_to_user(
        data.recipient_id,
        "new_message",
        {
            "message_id": message.id,
            "sender_id": current_user.id,
            "sender_username": current_user.username,
        },
    )

    return _message_to_public(
        message,
        device_keys=[
            DeviceKeyEntry(device_id=dk.device_id, encrypted_key=dk.encrypted_key)
            for dk in data.device_keys
        ],
    )


@router.get("", response_model=list[ConversationSummary])
async def get_inbox(
    current_user: CurrentUser,
    db: DBSession,
    device_id: int | None = Query(
        None, description="Requesting device ID for decryption key"
    ),
):
    """
    List all conversations for the authenticated user, newest first.
    Returns one entry per conversation partner with the last message time,
    unread count, and the requesting device's key for the last message preview.
    """
    uid = current_user.id

    # Fetch IDs of users blocked in either direction to exclude from inbox
    from app.crud.block import get_blocked_user_ids

    blocked_ids = await get_blocked_user_ids(db, uid)

    other_user_id = case(
        (Message.sender_id == uid, Message.recipient_id),
        else_=Message.sender_id,
    ).label("other_user_id")

    unread_count = func.sum(
        case(
            ((Message.recipient_id == uid) & (Message.is_read == False), 1),  # noqa: E712
            else_=0,
        )
    ).label("unread_count")

    subq = (
        select(
            other_user_id,
            func.max(Message.created_at).label("last_message_at"),
            func.max(Message.id).label("last_message_id"),
            unread_count,
        )
        .where(or_(Message.sender_id == uid, Message.recipient_id == uid))
        .group_by(other_user_id)
        .subquery()
    )

    inbox_query = (
        select(
            subq.c.other_user_id,
            User.username.label("other_username"),
            User.avatar_url.label("other_avatar_url"),
            subq.c.last_message_at,
            subq.c.unread_count,
            subq.c.last_message_id,
        )
        .join(User, User.id == subq.c.other_user_id)
        .order_by(subq.c.last_message_at.desc())
    )
    if blocked_ids:
        inbox_query = inbox_query.where(subq.c.other_user_id.notin_(blocked_ids))

    result = await db.execute(inbox_query)

    from app.core.media_urls import resolve_urls

    rows = result.all()

    # Batch-fetch last messages
    last_msg_ids = [row.last_message_id for row in rows if row.last_message_id]
    last_msgs: dict[int, Message] = {}
    if last_msg_ids:
        msg_result = await db.execute(
            select(Message).where(Message.id.in_(last_msg_ids))
        )
        for m in msg_result.scalars():
            last_msgs[m.id] = m

    # Batch-fetch device keys for last messages (for the requesting device)
    device_keys_map: dict[int, str] = {}
    if device_id and last_msg_ids:
        dk_result = await db.execute(
            select(MessageDeviceKey).where(
                MessageDeviceKey.message_id.in_(last_msg_ids),
                MessageDeviceKey.device_id == device_id,
            )
        )
        for mdk in dk_result.scalars():
            device_keys_map[mdk.message_id] = mdk.encrypted_key

    avatar_keys = [row.other_avatar_url for row in rows]
    resolved = await resolve_urls(avatar_keys)
    summaries = []
    for i, row in enumerate(rows):
        lm = last_msgs.get(row.last_message_id) if row.last_message_id else None
        summaries.append(
            ConversationSummary(
                other_user_id=row.other_user_id,
                other_username=row.other_username,
                other_avatar_url=resolved[i],
                last_message_at=row.last_message_at,
                unread_count=row.unread_count,
                last_message_id=row.last_message_id,
                last_message_ciphertext=None
                if (lm and lm.is_deleted)
                else (lm.ciphertext if lm else None),
                last_message_device_key=None
                if (lm and lm.is_deleted)
                else device_keys_map.get(row.last_message_id),
                last_message_sender_id=lm.sender_id if lm else None,
                last_message_is_deleted=lm.is_deleted if lm else False,
            )
        )
    return summaries


@router.get("/single/{message_id}", response_model=MessagePublic)
async def get_single_message(
    message_id: int,
    current_user: CurrentUser,
    db: DBSession,
    device_id: int | None = Query(None, description="Requesting device ID"),
):
    """Fetch a single message by ID. Only the sender or recipient may access it."""
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if msg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found")
    if msg.sender_id != current_user.id and msg.recipient_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your message")

    # Fetch device keys for this message + device
    dk_map = await _device_keys_for_messages(db, [msg.id], device_id)
    device_keys = dk_map.get(msg.id, [])

    # Enrich shared post if present
    shared_post = None
    if msg.shared_post_id:
        previews = await _enrich_shared_posts(db, [msg])
        shared_post = previews.get(msg.shared_post_id)

    return _message_to_public(msg, device_keys=device_keys, shared_post=shared_post)


@router.get("/{other_user_id}", response_model=list[MessagePublic])
async def get_conversation(
    other_user_id: int,
    current_user: CurrentUser,
    db: DBSession,
    before_id: int | None = Query(
        None, description="Cursor: fetch messages older than this ID"
    ),
    device_id: int | None = Query(None, description="Requesting device ID"),
):
    """Retrieve the conversation thread with another user, newest first.
    Supports cursor pagination via ``before_id``."""
    from app.crud.block import is_blocked_either_direction

    if await is_blocked_either_direction(db, current_user.id, other_user_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Cannot view this conversation"
        )

    query = select(Message).where(
        or_(
            (Message.sender_id == current_user.id)
            & (Message.recipient_id == other_user_id),
            (Message.sender_id == other_user_id)
            & (Message.recipient_id == current_user.id),
        )
    )
    if before_id is not None:
        query = query.where(Message.id < before_id)
    result = await db.execute(query.order_by(Message.created_at.desc()).limit(50))
    messages = list(result.scalars().all())

    # Batch-fetch device keys
    msg_ids = [m.id for m in messages]
    dk_map = await _device_keys_for_messages(db, msg_ids, device_id)

    # Enrich shared posts
    post_previews = await _enrich_shared_posts(db, messages)

    results = []
    for m in messages:
        results.append(
            _message_to_public(
                m,
                device_keys=dk_map.get(m.id, []),
                shared_post=post_previews.get(m.shared_post_id)
                if m.shared_post_id
                else None,
            )
        )
    return results


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_message(
    request: Request, message_id: int, current_user: CurrentUser, db: DBSession
):
    """
    Delete a message for everyone.
    Only the sender can delete, and only within 1 hour of sending.
    The message is kept as a tombstone (is_deleted=True) visible to both parties.
    """
    from datetime import datetime, timedelta, timezone

    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if msg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found")
    if msg.sender_id != current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only the sender can delete a message"
        )
    if msg.is_deleted:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Message already deleted"
        )
    if datetime.now(timezone.utc) - msg.created_at.replace(
        tzinfo=timezone.utc
    ) > timedelta(hours=1):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Messages can only be deleted within 1 hour of sending",
        )

    msg.is_deleted = True
    msg.ciphertext = ""
    # Clean up per-device wrapped keys (no longer needed for tombstoned message)
    await db.execute(
        delete(MessageDeviceKey).where(MessageDeviceKey.message_id == msg.id)
    )
    await db.commit()

    await publish_to_user(
        msg.recipient_id,
        "message_deleted",
        {"message_id": msg.id},
    )


@router.patch("/{other_user_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_as_read(other_user_id: int, current_user: CurrentUser, db: DBSession):
    """
    Mark all messages from other_user_id to the current user as read.
    Call this when the user opens a conversation.
    Publishes a ``messages_read`` WS event so the sender sees blue checkmarks.
    """
    from app.crud.block import is_blocked_either_direction

    if await is_blocked_either_direction(db, current_user.id, other_user_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Cannot interact with this user"
        )

    result = await db.execute(
        update(Message)
        .where(
            Message.sender_id == other_user_id,
            Message.recipient_id == current_user.id,
            Message.is_read == False,  # noqa: E712
        )
        .values(is_read=True)
        .returning(Message.id)
    )
    read_ids = [row[0] for row in result.all()]
    await db.commit()

    if read_ids:
        await publish_to_user(
            other_user_id,
            "messages_read",
            {"reader_id": current_user.id, "message_ids": read_ids},
        )
