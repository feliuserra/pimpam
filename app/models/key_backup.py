"""
Server-side encrypted key backup.

The private key is wrapped client-side with a passphrase-derived key
(Argon2id) and uploaded as an opaque encrypted blob. The server never
sees the plaintext private key or the passphrase.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class KeyBackup(Base):
    __tablename__ = "key_backups"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("user_devices.id"), nullable=False
    )
    encrypted_private_key: Mapped[str] = mapped_column(Text, nullable=False)
    salt: Mapped[str] = mapped_column(String(44), nullable=False)
    kdf: Mapped[str] = mapped_column(String(20), nullable=False, default="argon2id")
    kdf_params: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (UniqueConstraint("user_id", "device_id"),)
