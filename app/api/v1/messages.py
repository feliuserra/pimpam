from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select

from app.core.dependencies import CurrentUser, DBSession
from app.models.message import Message
from app.schemas.message import MessagePublic, MessageSend

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("", response_model=MessagePublic, status_code=status.HTTP_201_CREATED)
async def send_message(data: MessageSend, current_user: CurrentUser, db: DBSession):
    """
    Send an E2EE message. The server stores only ciphertext.
    Encryption must be done client-side before calling this endpoint.
    """
    if data.recipient_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot message yourself")

    message = Message(
        sender_id=current_user.id,
        recipient_id=data.recipient_id,
        ciphertext=data.ciphertext,
        encrypted_key=data.encrypted_key,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


@router.get("/{other_user_id}", response_model=list[MessagePublic])
async def get_conversation(other_user_id: int, current_user: CurrentUser, db: DBSession):
    """Retrieve the conversation thread with another user, newest first."""
    result = await db.execute(
        select(Message)
        .where(
            or_(
                (Message.sender_id == current_user.id) & (Message.recipient_id == other_user_id),
                (Message.sender_id == other_user_id) & (Message.recipient_id == current_user.id),
            )
        )
        .order_by(Message.created_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())
