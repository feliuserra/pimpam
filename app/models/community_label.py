from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class CommunityLabel(Base):
    """Mod-created label for organizing posts within a community."""

    __tablename__ = "community_labels"
    __table_args__ = (UniqueConstraint("community_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
