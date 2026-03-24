from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(2048))
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    community_id: Mapped[int | None] = mapped_column(ForeignKey("communities.id"))
    karma: Mapped[int] = mapped_column(Integer, default=1)  # starts at 1 (author's implicit vote)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Edit tracking — history is not public, only the flag is
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Moderation — removed posts are hidden from public but visible to moderators
    is_removed: Mapped[bool] = mapped_column(Boolean, default=False)
    removed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    # Uploaded image — URL pointing to S3-compatible storage (WebP, processed server-side)
    image_url: Mapped[str | None] = mapped_column(String(2048))

    # ActivityPub federation — stores the remote post's URL for federated content
    ap_id: Mapped[str | None] = mapped_column(String(2048), unique=True)

    # Shares — when set, this post is a reshare of another post
    shared_from_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id"), nullable=True)
    share_comment: Mapped[str | None] = mapped_column(String(300))

    # Relationships
    author: Mapped["User"] = relationship(foreign_keys=[author_id], back_populates="posts", lazy="raise")
    community: Mapped["Community | None"] = relationship(back_populates="posts", lazy="raise")
    shared_from: Mapped["Post | None"] = relationship(foreign_keys=[shared_from_id], lazy="raise")
