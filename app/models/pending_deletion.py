from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class PendingDeletion(Base):
    """Queue of S3 objects scheduled for deletion after a grace period.

    Objects stay in S3 for 1 hour after replacement/removal so that any
    cached signed URLs remain valid until they expire.
    """

    __tablename__ = "pending_deletions"

    id: Mapped[int] = mapped_column(primary_key=True)
    s3_key: Mapped[str] = mapped_column(String(2048), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    delete_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    bytes_to_reclaim: Mapped[int] = mapped_column(Integer, default=0)
