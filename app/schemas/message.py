from datetime import datetime

from pydantic import BaseModel


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
    is_deleted: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    """One entry per conversation in the inbox, ordered by most recent message."""

    other_user_id: int
    other_username: str
    other_avatar_url: str | None = None
    last_message_at: datetime
    unread_count: int
    last_message_id: int | None = None
    last_message_ciphertext: str | None = None
    last_message_encrypted_key: str | None = None
    last_message_sender_encrypted_key: str | None = None
    last_message_sender_id: int | None = None
    last_message_is_deleted: bool = False
