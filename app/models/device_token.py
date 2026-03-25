from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class DeviceToken(Base):
    __tablename__ = "device_tokens"
    __table_args__ = (UniqueConstraint("user_id", "token"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(500), nullable=False)
    platform: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # "ios", "android", or "web"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
