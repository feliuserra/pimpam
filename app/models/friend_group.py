from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class FriendGroup(Base):
    __tablename__ = "friend_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # True for the one special "Close Friends" group per user (auto-created, cannot be renamed/deleted)
    is_close_friends: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    members: Mapped[list["FriendGroupMember"]] = relationship(
        "FriendGroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="raise",
    )


class FriendGroupMember(Base):
    __tablename__ = "friend_group_members"
    __table_args__ = (UniqueConstraint("group_id", "member_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("friend_groups.id"), index=True, nullable=False)
    member_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    group: Mapped["FriendGroup"] = relationship(back_populates="members", lazy="raise")
