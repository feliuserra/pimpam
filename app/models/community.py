from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.user import User


class Community(Base):
    __tablename__ = "communities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    is_news: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    owner: Mapped["User"] = relationship(lazy="raise")
    posts: Mapped[list["Post"]] = relationship(back_populates="community", lazy="raise")
    members: Mapped[list["CommunityMember"]] = relationship(
        back_populates="community", lazy="raise"
    )


class CommunityMember(Base):
    __tablename__ = "community_members"
    __table_args__ = (UniqueConstraint("community_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int] = mapped_column(
        ForeignKey("communities.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="member")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    community: Mapped["Community"] = relationship(
        back_populates="members", lazy="raise"
    )
    user: Mapped["User"] = relationship(lazy="raise")
