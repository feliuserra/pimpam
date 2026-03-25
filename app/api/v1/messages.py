from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import case, func, or_, select, update

from app.core.dependencies import CurrentUser, DBSession
from app.core.limiter import limiter
from app.core.redis import publish_to_user
from app.crud.user import get_user_by_id
from app.models.message import Message
from app.models.user import User
from app.schemas.message import ConversationSummary, MessagePublic, MessageSend

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

    message = Message(
        sender_id=current_user.id,
        recipient_id=data.recipient_id,
        ciphertext=data.ciphertext,
        encrypted_key=data.encrypted_key,
        sender_encrypted_key=data.sender_encrypted_key,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    await publish_to_user(
        data.recipient_id,
        "new_message",
        {
            "sender_id": current_user.id,
            "sender_username": current_user.username,
        },
    )

    return message


@router.get("", response_model=list[ConversationSummary])
async def get_inbox(current_user: CurrentUser, db: DBSession):
    """
    List all conversations for the authenticated user, newest first.
    Returns one entry per conversation partner with the last message time and unread count.
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
            subq.c.last_message_at,
            subq.c.unread_count,
        )
        .join(User, User.id == subq.c.other_user_id)
        .order_by(subq.c.last_message_at.desc())
    )

    return [
        ConversationSummary(
            other_user_id=row.other_user_id,
            other_username=row.other_username,
            last_message_at=row.last_message_at,
            unread_count=row.unread_count,
        )
        for row in result.all()
    ]


@router.get("/{other_user_id}", response_model=list[MessagePublic])
async def get_conversation(
    other_user_id: int, current_user: CurrentUser, db: DBSession
):
    """Retrieve the conversation thread with another user, newest first."""
    result = await db.execute(
        select(Message)
        .where(
            or_(
                (Message.sender_id == current_user.id)
                & (Message.recipient_id == other_user_id),
                (Message.sender_id == other_user_id)
                & (Message.recipient_id == current_user.id),
            )
        )
        .order_by(Message.created_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


@router.patch("/{other_user_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_as_read(other_user_id: int, current_user: CurrentUser, db: DBSession):
    """
    Mark all messages from other_user_id to the current user as read.
    Call this when the user opens a conversation.
    """
    await db.execute(
        update(Message)
        .where(
            Message.sender_id == other_user_id,
            Message.recipient_id == current_user.id,
            Message.is_read == False,  # noqa: E712
        )
        .values(is_read=True)
    )
    await db.commit()
