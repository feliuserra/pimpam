from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Issue(Base):
    """Community-submitted bug report or feature request, voted on democratically."""

    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # bug, feature, improvement
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open"
    )  # open, in_progress, completed, rejected
    vote_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    device_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Security items are non-negotiable — cannot be voted down or rejected by community
    is_security: Mapped[bool] = mapped_column(Boolean, default=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class IssueVote(Base):
    """One upvote per user per issue."""

    __tablename__ = "issue_votes"
    __table_args__ = (UniqueConstraint("issue_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class IssueComment(Base):
    """Discussion on an issue."""

    __tablename__ = "issue_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class IssuePoll(Base):
    """Optional poll attached to an issue (one poll per issue)."""

    __tablename__ = "issue_polls"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    question: Mapped[str] = mapped_column(String(300), nullable=False)
    allows_multiple: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class IssuePollOption(Base):
    """One option in an issue poll."""

    __tablename__ = "issue_poll_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    poll_id: Mapped[int] = mapped_column(
        ForeignKey("issue_polls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(String(200), nullable=False)
    vote_count: Mapped[int] = mapped_column(Integer, default=0)
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class IssuePollVote(Base):
    """One vote per user per poll option."""

    __tablename__ = "issue_poll_votes"
    __table_args__ = (UniqueConstraint("option_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    option_id: Mapped[int] = mapped_column(
        ForeignKey("issue_poll_options.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
