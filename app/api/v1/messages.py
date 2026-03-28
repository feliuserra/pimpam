from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import case, func, or_, select, update

from app.core.dependencies import CurrentUser, DBSession
from app.core.limiter import limiter
from app.core.redis import publish_to_user
from app.crud.user import get_user_by_id
from app.models.message import Message
from app.models.user import User
from app.schemas.message import (
    ConversationSummary,
    MessagePublic,
    MessageSend,
    SharedPostPreview,
)

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("", response_model=MessagePublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def send_message(
    request: Request, data: MessageSend, current_user: CurrentUser, db: DBSession
):
    """
    Send an E2EE message. The server stores only ciphertext.
    Encryption must be done client-side before calling this endpoint.
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
        encrypted_key=data.encrypted_key,
        sender_encrypted_key=data.sender_encrypted_key,
        shared_post_id=shared_post_id,
    )
    db.add(message)
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

    return message


@router.get("", response_model=list[ConversationSummary])
async def get_inbox(current_user: CurrentUser, db: DBSession):
    """
    List all conversations for the authenticated user, newest first.
    Returns one entry per conversation partner with the last message time,
    unread count, and encrypted last message fields for client-side preview.
    """
    uid = current_user.id

    # Derive the "other" participant in each message
    other_user_id = case(
        (Message.sender_id == uid, Message.recipient_id),
        else_=Message.sender_id,
    ).label("other_user_id")

    # Count unread messages received by current user in each conversation
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

    result = await db.execute(
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

    from app.core.media_urls import resolve_urls

    rows = result.all()

    # Batch-fetch last messages to include encrypted data for preview
    last_msg_ids = [row.last_message_id for row in rows if row.last_message_id]
    last_msgs: dict[int, Message] = {}
    if last_msg_ids:
        msg_result = await db.execute(
            select(Message).where(Message.id.in_(last_msg_ids))
        )
        for m in msg_result.scalars():
            last_msgs[m.id] = m

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
                last_message_encrypted_key=None
                if (lm and lm.is_deleted)
                else (lm.encrypted_key if lm else None),
                last_message_sender_encrypted_key=None
                if (lm and lm.is_deleted)
                else (lm.sender_encrypted_key if lm else None),
                last_message_sender_id=lm.sender_id if lm else None,
                last_message_is_deleted=lm.is_deleted if lm else False,
            )
        )
    return summaries


@router.get("/single/{message_id}", response_model=MessagePublic)
async def get_single_message(message_id: int, current_user: CurrentUser, db: DBSession):
    """Fetch a single message by ID. Only the sender or recipient may access it."""
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if msg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found")
    if msg.sender_id != current_user.id and msg.recipient_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your message")

    pub = MessagePublic.model_validate(msg, from_attributes=True)

    # Enrich shared post if present
    if msg.shared_post_id:
        from app.models.post import Post

        post_row = await db.execute(select(Post).where(Post.id == msg.shared_post_id))
        post = post_row.scalar_one_or_none()
        if post and not post.is_removed:
            author_data: tuple[str | None, str | None] = (None, None)
            if post.author_id:
                a_row = await db.execute(
                    select(User.username, User.avatar_url).where(
                        User.id == post.author_id
                    )
                )
                a = a_row.one_or_none()
                if a:
                    author_data = (a.username, a.avatar_url)

            community_name = None
            if post.community_id:
                from app.models.community import Community

                c_row = await db.execute(
                    select(Community.name).where(Community.id == post.community_id)
                )
                community_name = c_row.scalar_one_or_none()

            from app.core.media_urls import resolve_urls as _resolve_urls

            resolved = await _resolve_urls([post.image_url, author_data[1]])
            pub = pub.model_copy(
                update={
                    "shared_post": SharedPostPreview(
                        id=post.id,
                        title=post.title,
                        content=(post.content[:200] + "...")
                        if post.content and len(post.content) > 200
                        else post.content,
                        image_url=resolved[0],
                        author_username=author_data[0],
                        author_avatar_url=resolved[1],
                        community_name=community_name,
                        karma=post.karma,
                    )
                }
            )

    if msg.is_deleted:
        pub = pub.model_copy(
            update={
                "ciphertext": "",
                "encrypted_key": "",
                "sender_encrypted_key": None,
            }
        )
    return pub


@router.get("/{other_user_id}", response_model=list[MessagePublic])
async def get_conversation(
    other_user_id: int,
    current_user: CurrentUser,
    db: DBSession,
    before_id: int | None = Query(
        None, description="Cursor: fetch messages older than this ID"
    ),
):
    """Retrieve the conversation thread with another user, newest first.
    Supports cursor pagination via ``before_id``."""
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

    # Enrich messages that contain shared posts
    shared_ids = [m.shared_post_id for m in messages if m.shared_post_id]
    post_previews: dict[int, SharedPostPreview] = {}
    if shared_ids:
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
                select(Community.id, Community.name).where(
                    Community.id.in_(community_ids)
                )
            )
            for r in c_rows:
                communities[r.id] = r.name

        from app.core.media_urls import resolve_urls as _resolve_urls

        # Resolve all image keys in batch
        _img_keys = [p.image_url for p in posts]
        _avatar_keys = [authors.get(p.author_id, (None, None))[1] for p in posts]
        _resolved = await _resolve_urls(_img_keys + _avatar_keys)
        _resolved_imgs = _resolved[: len(posts)]
        _resolved_avs = _resolved[len(posts) :]

        for idx, p in enumerate(posts):
            author_data = authors.get(p.author_id, (None, None))
            post_previews[p.id] = SharedPostPreview(
                id=p.id,
                title=p.title,
                content=(p.content[:200] + "...")
                if p.content and len(p.content) > 200
                else p.content,
                image_url=_resolved_imgs[idx],
                author_username=author_data[0],
                author_avatar_url=_resolved_avs[idx],
                community_name=communities.get(p.community_id)
                if p.community_id
                else None,
                karma=p.karma,
            )

    results = []
    for m in messages:
        pub = MessagePublic.model_validate(m, from_attributes=True)
        if m.shared_post_id:
            pub = pub.model_copy(
                update={"shared_post": post_previews.get(m.shared_post_id)}
            )
        # Tombstone: clear ciphertext so the client shows "[deleted]"
        if m.is_deleted:
            pub = pub.model_copy(
                update={
                    "ciphertext": "",
                    "encrypted_key": "",
                    "sender_encrypted_key": None,
                }
            )
        results.append(pub)
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
    msg.encrypted_key = ""
    msg.sender_encrypted_key = None
    await db.commit()

    # Notify the recipient in real time
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

    # Notify the sender so they see blue ✓✓ in real time
    if read_ids:
        await publish_to_user(
            other_user_id,
            "messages_read",
            {"reader_id": current_user.id, "message_ids": read_ids},
        )
