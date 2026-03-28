from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class LoginAttempt(Base):
    """
    Privacy-respecting audit log of login attempts.

    - No user_id: a failed login does not authenticate anyone; storing a user_id on
      failures would link a security event to a specific account without consent.
    - ip_hash: SHA-256 hex of the client IP, never plaintext (mirrors ConsentLog).
    - Auto-purged after 30 days by the background cleanup loop in main.py.
    """

    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    # SHA-256 hex of client IP — never stored in plaintext
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        # Covers the "same IP, many failures in window" query without a table scan
        Index(
            "ix_login_attempts_ip_hash_success_created",
            "ip_hash",
            "success",
            "created_at",
        ),
    )
