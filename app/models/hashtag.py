from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Hashtag(Base):
    """Normalized hashtag — stores the canonical lowercase name and usage count."""

    __tablename__ = "hashtags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    post_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class PostHashtag(Base):
    """Association between a post and a hashtag."""

    __tablename__ = "post_hashtags"
    __table_args__ = (UniqueConstraint("post_id", "hashtag_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hashtag_id: Mapped[int] = mapped_column(
        ForeignKey("hashtags.id", ondelete="CASCADE"), nullable=False, index=True
    )
