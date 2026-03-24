from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False)

    # Who triggered the notification (None for system events like bans)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Context references — whichever are relevant for the type
    post_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id"), nullable=True)
    comment_id: Mapped[int | None] = mapped_column(ForeignKey("comments.id"), nullable=True)
    community_id: Mapped[int | None] = mapped_column(ForeignKey("communities.id"), nullable=True)

    # Grouping — reactions and votes are aggregated into a single unread row
    group_key: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    group_count: Mapped[int] = mapped_column(Integer, default=1)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


class NotificationPreference(Base):
    """
    Opt-out list per user. Presence of a row means the notification type is DISABLED.
    All types are enabled by default — no rows needed.
    """
    __tablename__ = "notification_preferences"
    __table_args__ = (UniqueConstraint("user_id", "notification_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(40), nullable=False)
