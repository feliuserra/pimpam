"""
Moderation models: bans, ban proposals, moderator promotion proposals,
ban appeals, and ownership transfers.

Ban flow:
  1. Any moderator opens a BanProposal with a CoC violation reason.
  2. Other moderators cast BanProposalVotes.
  3. Once vote_count reaches required_votes (min 10), a Ban is auto-created.

Ban appeal flow:
  1. A banned user submits a BanAppeal with a reason.
  2. Moderators who did NOT vote on the original ban cast BanAppealVotes.
  3. Once vote_count reaches required_votes (10), the ban is overturned.

Moderator promotion flow:
  1. Any senior_mod+ opens a ModProposal for a community member.
  2. Other senior_mods+ cast ModProposalVotes.
  3. Once a majority agree (min 2), the member is promoted.

Ownership transfer flow:
  1. Any senior_mod+ proposes a transfer to a community member.
  2. The recipient accepts or rejects.
  3. On accept: old owner becomes moderator, new owner gets role="owner".
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
    status: Mapped[str] = mapped_column(String(20), default="active")  # "active" | "overturned"
    proposal_id: Mapped[int | None] = mapped_column(ForeignKey("ban_proposals.id"), nullable=True)
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


class BanAppeal(Base):
    __tablename__ = "ban_appeals"

    id: Mapped[int] = mapped_column(primary_key=True)
    ban_id: Mapped[int] = mapped_column(ForeignKey("bans.id"), nullable=False, index=True)
    appellant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # "pending"|"approved"|"rejected"
    vote_count: Mapped[int] = mapped_column(Integer, default=0)
    required_votes: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    votes: Mapped[list["BanAppealVote"]] = relationship(back_populates="appeal", lazy="raise")


class BanAppealVote(Base):
    __tablename__ = "ban_appeal_votes"
    __table_args__ = (UniqueConstraint("appeal_id", "voter_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    appeal_id: Mapped[int] = mapped_column(ForeignKey("ban_appeals.id"), nullable=False)
    voter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    appeal: Mapped["BanAppeal"] = relationship(back_populates="votes", lazy="raise")


class ModProposal(Base):
    """
    Proposal to promote a community member to moderator or senior_mod.
    Requires majority of current senior_mods+ (minimum 2) to approve.
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
    target_role: Mapped[str] = mapped_column(String(20), default="moderator")
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


class OwnershipTransfer(Base):
    __tablename__ = "ownership_transfers"

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int] = mapped_column(ForeignKey("communities.id"), nullable=False, index=True)
    proposed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # "pending"|"accepted"|"rejected"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
