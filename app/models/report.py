from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("reporter_id", "content_type", "content_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # "post" or "comment"
    content_id: Mapped[int] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
