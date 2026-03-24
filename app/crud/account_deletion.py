"""
Account deletion logic.

schedule_deletion  — sets the 7-day grace period
cancel_deletion    — clears it
execute_deletion   — performs the irreversible hard delete (called by background task)
process_pending_deletions  — finds due accounts and deletes them
process_expired_unverified — purges unverified accounts older than N days
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.comment import Comment, CommentReaction
from app.models.community import CommunityMember
from app.models.community_karma import CommunityKarma
from app.models.follow import Follow
from app.models.message import Message
from app.models.moderation import (
    Ban,
    BanAppeal,
    BanAppealVote,
    BanProposal,
    BanProposalVote,
    ModProposal,
    ModProposalVote,
    OwnershipTransfer,
)
from app.models.notification import Notification
from app.models.password_reset import PasswordResetToken
from app.models.post import Post
from app.models.user import User
from app.models.vote import Vote


async def schedule_deletion(db: AsyncSession, user: User) -> None:
    """Mark an account for deletion in `account_deletion_grace_days` days."""
    user.deletion_scheduled_at = datetime.now(timezone.utc) + timedelta(
        days=settings.account_deletion_grace_days
    )
    await db.commit()


async def cancel_deletion(db: AsyncSession, user: User) -> None:
    """Cancel a pending deletion request."""
    user.deletion_scheduled_at = None
    await db.commit()


async def execute_deletion(db: AsyncSession, user_id: int) -> None:
    """
    Hard-delete a user account and anonymize/remove all associated data.

    Order matters — child rows must be removed before parent rows to satisfy
    FK constraints. Posts and comments keep their rows but author_id is nulled
    (shown as "[deleted user]" by clients). Messages sent by this user are
    anonymized; messages they received are deleted. Everything else is purged.
    """
    # --- Moderation: delete in dependency order ---

    # Collect IDs for cascading deletes
    bp_ids_result = await db.execute(
        select(BanProposal.id).where(
            or_(BanProposal.target_user_id == user_id, BanProposal.proposed_by_id == user_id)
        )
    )
    bp_ids = [r[0] for r in bp_ids_result]

    ban_ids_result = await db.execute(select(Ban.id).where(Ban.user_id == user_id))
    ban_ids = [r[0] for r in ban_ids_result]

    appeal_ids_result = await db.execute(
        select(BanAppeal.id).where(
            or_(
                BanAppeal.appellant_id == user_id,
                *(
                    [BanAppeal.ban_id.in_(ban_ids)] if ban_ids else []
                ),
            )
        )
    )
    appeal_ids = [r[0] for r in appeal_ids_result]

    mp_ids_result = await db.execute(
        select(ModProposal.id).where(
            or_(ModProposal.target_user_id == user_id, ModProposal.proposed_by_id == user_id)
        )
    )
    mp_ids = [r[0] for r in mp_ids_result]

    if appeal_ids:
        await db.execute(delete(BanAppealVote).where(BanAppealVote.appeal_id.in_(appeal_ids)))
    await db.execute(delete(BanAppealVote).where(BanAppealVote.voter_id == user_id))

    if appeal_ids:
        await db.execute(delete(BanAppeal).where(BanAppeal.id.in_(appeal_ids)))

    if bp_ids:
        await db.execute(delete(BanProposalVote).where(BanProposalVote.proposal_id.in_(bp_ids)))
    await db.execute(delete(BanProposalVote).where(BanProposalVote.voter_id == user_id))

    if bp_ids:
        await db.execute(delete(BanProposal).where(BanProposal.id.in_(bp_ids)))

    await db.execute(delete(Ban).where(Ban.user_id == user_id))

    if mp_ids:
        await db.execute(delete(ModProposalVote).where(ModProposalVote.proposal_id.in_(mp_ids)))
    await db.execute(delete(ModProposalVote).where(ModProposalVote.voter_id == user_id))

    if mp_ids:
        await db.execute(delete(ModProposal).where(ModProposal.id.in_(mp_ids)))

    await db.execute(
        delete(OwnershipTransfer).where(
            or_(OwnershipTransfer.proposed_by_id == user_id, OwnershipTransfer.recipient_id == user_id)
        )
    )

    # --- Social data ---
    await db.execute(delete(Notification).where(Notification.user_id == user_id))
    await db.execute(
        update(Notification)
        .where(Notification.actor_id == user_id)
        .values(actor_id=None)
    )
    await db.execute(delete(CommentReaction).where(CommentReaction.user_id == user_id))
    await db.execute(delete(Vote).where(Vote.user_id == user_id))
    await db.execute(delete(CommunityKarma).where(CommunityKarma.user_id == user_id))
    await db.execute(delete(CommunityMember).where(CommunityMember.user_id == user_id))
    await db.execute(
        delete(Follow).where(or_(Follow.follower_id == user_id, Follow.followed_id == user_id))
    )
    await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id))

    # --- Messages ---
    # Anonymize sent messages (other party keeps them as from "[deleted]")
    await db.execute(
        update(Message).where(Message.sender_id == user_id).values(sender_id=None)
    )
    # Remove received messages (user's inbox is gone)
    await db.execute(delete(Message).where(Message.recipient_id == user_id))

    # --- Content: anonymize, keep the posts/comments ---
    await db.execute(update(Post).where(Post.author_id == user_id).values(author_id=None))
    await db.execute(update(Comment).where(Comment.author_id == user_id).values(author_id=None))

    # --- User row ---
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()


async def process_pending_deletions(db: AsyncSession) -> int:
    """Execute all accounts whose grace period has expired. Returns count deleted."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(User.id).where(
            User.deletion_scheduled_at.is_not(None),
            User.deletion_scheduled_at <= now,
        )
    )
    ids = [r[0] for r in result]
    for user_id in ids:
        await execute_deletion(db, user_id)
    return len(ids)


async def process_expired_unverified(db: AsyncSession) -> int:
    """Delete unverified accounts older than `unverified_account_delete_days`. Returns count."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.unverified_account_delete_days)
    result = await db.execute(
        select(User.id).where(User.is_verified == False, User.created_at <= cutoff)  # noqa: E712
    )
    ids = [r[0] for r in result]
    for user_id in ids:
        await execute_deletion(db, user_id)
    return len(ids)
