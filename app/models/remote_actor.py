from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class RemoteActor(Base):
    """
    Cache of remote ActivityPub actor documents.
    Avoids re-fetching the public key on every incoming request.
    Invalidated by TTL (see settings.remote_actor_cache_ttl_seconds).
    """

    __tablename__ = "remote_actors"

    # The canonical AP actor URL is used as the natural key
    ap_id: Mapped[str] = mapped_column(String(2048), primary_key=True)
    username: Mapped[str] = mapped_column(String(255))
    domain: Mapped[str] = mapped_column(String(255), index=True)
    inbox_url: Mapped[str] = mapped_column(String(2048))
    shared_inbox_url: Mapped[str | None] = mapped_column(String(2048))
    public_key_pem: Mapped[str] = mapped_column(Text)
    # Full actor document stored as JSON for fields we don't explicitly model
    actor_json: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
