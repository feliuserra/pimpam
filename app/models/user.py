from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.follow import Follow
    from app.models.post import Post


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(String(2048))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    karma: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Incremented on password reset / logout to invalidate all outstanding refresh tokens
    token_version: Mapped[int] = mapped_column(Integer, default=0)

    # Account deletion — set when user requests deletion; background task hard-deletes after 7 days
    deletion_scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # Email verification — token hash stored here (no separate table; one token per user at a time)
    email_verification_token_hash: Mapped[str | None] = mapped_column(String(64))
    email_verification_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # 2FA (TOTP) — secret is AES-encrypted at rest; totp_enabled stays False until user verifies a code
    totp_secret: Mapped[str | None] = mapped_column(String(512))  # Fernet ciphertext
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # ActivityPub federation fields
    ap_id: Mapped[str | None] = mapped_column(
        String(2048), unique=True
    )  # actor URL (local or remote)
    ap_inbox: Mapped[str | None] = mapped_column(String(2048))
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    # RSA key pair — generated at registration for local users; NULL for remote users
    ap_public_key_pem: Mapped[str | None] = mapped_column(Text)
    ap_private_key_pem: Mapped[str | None] = mapped_column(Text)

    # E2EE — client-published RSA-OAEP public key for DM encryption (base64-encoded SPKI)
    e2ee_public_key: Mapped[str | None] = mapped_column(Text)

    # Relationships
    posts: Mapped[list["Post"]] = relationship(
        foreign_keys="Post.author_id", back_populates="author", lazy="raise"
    )
    following: Mapped[list["Follow"]] = relationship(
        foreign_keys="Follow.follower_id", back_populates="follower", lazy="raise"
    )
    followers: Mapped[list["Follow"]] = relationship(
        foreign_keys="Follow.followed_id", back_populates="followed", lazy="raise"
    )
