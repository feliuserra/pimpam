from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(2048))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    community_id: Mapped[int | None] = mapped_column(ForeignKey("communities.id"))
    karma: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,  # indexed for chronological feed queries
    )

    # ActivityPub federation — stores the remote post's URL for federated content
    ap_id: Mapped[str | None] = mapped_column(String(2048), unique=True)

    # Relationships
    author: Mapped["User"] = relationship(back_populates="posts", lazy="raise")
    community: Mapped["Community | None"] = relationship(back_populates="posts", lazy="raise")
