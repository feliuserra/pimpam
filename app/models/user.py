from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(String(2048))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    karma: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # ActivityPub federation fields
    ap_id: Mapped[str | None] = mapped_column(String(2048), unique=True)  # actor URL (local or remote)
    ap_inbox: Mapped[str | None] = mapped_column(String(2048))
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    # RSA key pair — generated at registration for local users; NULL for remote users
    ap_public_key_pem: Mapped[str | None] = mapped_column(Text)
    ap_private_key_pem: Mapped[str | None] = mapped_column(Text)

    # Relationships
    posts: Mapped[list["Post"]] = relationship(foreign_keys="Post.author_id", back_populates="author", lazy="raise")
    following: Mapped[list["Follow"]] = relationship(
        foreign_keys="Follow.follower_id", back_populates="follower", lazy="raise"
    )
    followers: Mapped[list["Follow"]] = relationship(
        foreign_keys="Follow.followed_id", back_populates="followed", lazy="raise"
    )
