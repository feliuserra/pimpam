from datetime import datetime

from pydantic import BaseModel


class MessageSend(BaseModel):
    recipient_id: int
    ciphertext: str   # encrypted client-side — server never sees plaintext
    encrypted_key: str  # AES key wrapped with recipient's public key


class MessagePublic(BaseModel):
    id: int
    sender_id: int
    recipient_id: int
    ciphertext: str
    encrypted_key: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
