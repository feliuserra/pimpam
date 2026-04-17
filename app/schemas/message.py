from datetime import datetime

from pydantic import BaseModel, field_validator


class SharedPostPreview(BaseModel):
    """Minimal post data embedded in a DM for rich card rendering."""

    id: int
    title: str
    content: str | None = None
    image_url: str | None = None
    author_username: str | None = None
    author_avatar_url: str | None = None
    community_name: str | None = None
    karma: int = 0


class MessageSend(BaseModel):
    recipient_id: int
    ciphertext: str  # encrypted client-side — server never sees plaintext
    encrypted_key: str  # AES key wrapped with recipient's public key
    sender_encrypted_key: str | None = None  # AES key wrapped with sender's own key
    shared_post_id: int | None = None  # optional post shared via DM

    @field_validator("encrypted_key")
    @classmethod
    def validate_encrypted_key(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError(
                "encrypted_key is required — plaintext messages are not allowed"
            )
        return v


class MessagePublic(BaseModel):
    id: int
    sender_id: int
    recipient_id: int
    ciphertext: str
    encrypted_key: str
    sender_encrypted_key: str | None = None
    shared_post_id: int | None = None
    shared_post: SharedPostPreview | None = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    """One entry per conversation in the inbox, ordered by most recent message."""

    other_user_id: int
    other_username: str
    other_avatar_url: str | None = None
    last_message_at: datetime
    unread_count: int
