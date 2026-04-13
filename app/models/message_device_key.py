"""
Fan-out table for per-device message encryption keys.

When a message is sent, the sender wraps the AES session key once per
device (all active devices of both sender and recipient). Each row
stores one wrapped copy of that AES key for a specific device.
"""

from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class MessageDeviceKey(Base):
    __tablename__ = "message_device_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[int] = mapped_column(
        ForeignKey("user_devices.id"), nullable=False
    )
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("message_id", "device_id"),
        Index("ix_msg_device_keys_message", "message_id"),
        Index("ix_msg_device_keys_device", "device_id"),
    )
