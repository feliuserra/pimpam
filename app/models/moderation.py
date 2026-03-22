"""
Moderation models: bans, ban proposals, and moderator promotion proposals.

Ban flow:
  1. Any moderator opens a BanProposal with a CoC violation reason.
  2. Other moderators cast BanProposalVotes.
  3. Once vote_count reaches required_votes (min 10), a Ban is auto-created.

Moderator promotion flow:
  1. Any moderator opens a ModProposal for a community member.
  2. Other moderators cast ModProposalVotes.
  3. Once a majority of current moderators agree (min 2), the member is promoted.
"""
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class CoCViolation(str, Enum):
    """Code of Conduct violation categories for ban proposals."""
    HARASSMENT = "harassment"
    HATE_SPEECH = "hate_speech"
    ABUSE = "abuse"
    SPAM = "spam"
    IMPERSONATION = "impersonation"
    NSFW = "nsfw_without_warning"
    OTHER = "other"


class Ban(Base):
    __tablename__ = "bans"
    __table_args__ = (UniqueConstraint("community_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int] = mapped_column(ForeignKey("communities.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    coc_violation: Mapped[str] = mapped_column(String(50), nullable=False)
    is_permanent: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    community: Mapped["Community"] = relationship(lazy="raise")
    user: Mapped["User"] = relationship(lazy="raise")


class BanProposal(Base):
    __tablename__ = "ban_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int] = mapped_column(ForeignKey("communities.id"), nullable=False)
    target_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    proposed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    coc_violation: Mapped[str] = mapped_column(String(50), nullable=False)
    is_permanent: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    vote_count: Mapped[int] = mapped_column(Integer, default=0)
    required_votes: Mapped[int] = mapped_column(Integer, default=10)
    # pending | approved | rejected
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    votes: Mapped[list["BanProposalVote"]] = relationship(back_populates="proposal", lazy="raise")


class BanProposalVote(Base):
    __tablename__ = "ban_proposal_votes"
    __table_args__ = (UniqueConstraint("proposal_id", "voter_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("ban_proposals.id"), nullable=False)
    voter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    proposal: Mapped["BanProposal"] = relationship(back_populates="votes", lazy="raise")


class ModProposal(Base):
    """
    Proposal to promote a community member to moderator.
    Requires majority of current moderators (minimum 2) to approve.
    Threshold = max(2, ceil(current_mod_count / 2)).
    """

    __tablename__ = "mod_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int] = mapped_column(ForeignKey("communities.id"), nullable=False)
    target_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    proposed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    vote_count: Mapped[int] = mapped_column(Integer, default=0)
    required_votes: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    votes: Mapped[list["ModProposalVote"]] = relationship(back_populates="proposal", lazy="raise")


class ModProposalVote(Base):
    __tablename__ = "mod_proposal_votes"
    __table_args__ = (UniqueConstraint("proposal_id", "voter_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("mod_proposals.id"), nullable=False)
    voter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    proposal: Mapped["ModProposal"] = relationship(back_populates="votes", lazy="raise")
