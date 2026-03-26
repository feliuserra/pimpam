"""
Story model — ephemeral user content (images, links, or both + optional caption).

Stories expire after a user-chosen duration (default 24 h). There is no
"seen by" tracking — views are never recorded. Reported stories are
soft-deleted (is_removed=True) and retained for 48 h for mod review
before the hourly cleanup task permanently removes them.

media_type values: "image", "link", "link_image", "video" (future).
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    media_type: Mapped[str] = mapped_column(String(10), nullable=False, default="image")
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    caption: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Link story metadata — stored on the row to avoid re-fetching during ephemeral lifetime
    link_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    link_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    link_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    link_image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    is_removed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
