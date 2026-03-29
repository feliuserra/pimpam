from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User  # noqa: F401

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Message(Base):
    """
    End-to-end encrypted direct message.

    The server stores only ciphertext — it never sees plaintext content.
    Encryption is done client-side before the request is sent.
    Per-device wrapped AES keys are stored in the message_device_keys
    fan-out table (one row per device).
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Ciphertext only — server never holds plaintext.
    # Per-device wrapped AES keys live in message_device_keys (fan-out table).
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional: post shared as a DM (metadata — post content is public anyway)
    shared_post_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("posts.id", ondelete="SET NULL"), nullable=True
    )

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    # Deletion — tombstone visible to both parties
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationships
    sender: Mapped["User"] = relationship(foreign_keys=[sender_id], lazy="raise")
    recipient: Mapped["User"] = relationship(foreign_keys=[recipient_id], lazy="raise")

    __table_args__ = (
        Index("ix_messages_sender_created", "sender_id", "created_at"),
        Index("ix_messages_recipient_created", "recipient_id", "created_at"),
    )
