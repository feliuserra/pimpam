from sqlalchemy import Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class CommunityKarma(Base):
    __tablename__ = "community_karma"
    __table_args__ = (UniqueConstraint("user_id", "community_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    community_id: Mapped[int] = mapped_column(ForeignKey("communities.id"), nullable=False)
    karma: Mapped[int] = mapped_column(Integer, default=0)
