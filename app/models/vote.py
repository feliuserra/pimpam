from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Vote(Base):
    """
    A user's vote on a post. Direction is +1 or -1.

    Every post starts with a +1 vote from its author (created automatically
    on post creation). The author's vote cannot be retracted or changed.
    Users cannot vote on their own posts beyond that initial implicit upvote.
    """

    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("user_id", "post_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False, index=True)
    direction: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 or -1
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(lazy="raise")
    post: Mapped["Post"] = relationship(lazy="raise")
