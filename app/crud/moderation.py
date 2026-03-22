import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import CommunityMember
from app.models.moderation import (
    Ban,
    BanProposal,
    BanProposalVote,
    ModProposal,
    ModProposalVote,
)
from app.models.post import Post
from app.schemas.moderation import BanProposalCreate, ModProposalCreate


# --- Helpers ---

async def _mod_count(db: AsyncSession, community_id: int) -> int:
    result = await db.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.is_moderator == True,  # noqa: E712
        )
    )
    return len(result.scalars().all())


async def _is_moderator(db: AsyncSession, community_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == user_id,
            CommunityMember.is_moderator == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none() is not None


async def _is_banned(db: AsyncSession, community_id: int, user_id: int) -> bool:
    from datetime import datetime, timezone
    result = await db.execute(
        select(Ban).where(
            Ban.community_id == community_id,
            Ban.user_id == user_id,
        )
    )
    ban = result.scalar_one_or_none()
    if ban is None:
        return False
    if ban.is_permanent:
        return True
    return ban.expires_at is not None and ban.expires_at > datetime.now(timezone.utc)


# --- Post removal ---

async def remove_post(db: AsyncSession, post: Post, moderator_id: int) -> Post:
    """Hide a post. It remains in the DB and is visible to moderators."""
    post.is_removed = True
    post.removed_by_id = moderator_id
    await db.commit()
    await db.refresh(post)
    return post


async def restore_post(db: AsyncSession, post: Post) -> Post:
    """Undo a post removal."""
    post.is_removed = False
    post.removed_by_id = None
    await db.commit()
    await db.refresh(post)
    return post


# --- Ban proposals ---

async def propose_ban(
    db: AsyncSession,
    community_id: int,
    proposed_by_id: int,
    target_user_id: int,
    data: BanProposalCreate,
) -> BanProposal:
    proposal = BanProposal(
        community_id=community_id,
        target_user_id=target_user_id,
        proposed_by_id=proposed_by_id,
        reason=data.reason,
        coc_violation=data.coc_violation.value,
        is_permanent=data.is_permanent,
        expires_at=data.expires_at,
        vote_count=1,  # proposer's vote counts automatically
        required_votes=10,
    )
    db.add(proposal)
    await db.flush()

    # Proposer's vote
    db.add(BanProposalVote(proposal_id=proposal.id, voter_id=proposed_by_id))
    await db.commit()
    await db.refresh(proposal)
    return proposal


async def vote_ban_proposal(
    db: AsyncSession, proposal: BanProposal, voter_id: int
) -> BanProposal:
    """Cast a vote on a ban proposal. Auto-applies the ban when threshold is reached."""
    proposal.vote_count += 1
    db.add(BanProposalVote(proposal_id=proposal.id, voter_id=voter_id))

    if proposal.vote_count >= proposal.required_votes:
        proposal.status = "approved"
        # Apply the ban
        existing = await db.execute(
            select(Ban).where(Ban.community_id == proposal.community_id, Ban.user_id == proposal.target_user_id)
        )
        if existing.scalar_one_or_none() is None:
            db.add(Ban(
                community_id=proposal.community_id,
                user_id=proposal.target_user_id,
                reason=proposal.reason,
                coc_violation=proposal.coc_violation,
                is_permanent=proposal.is_permanent,
                expires_at=proposal.expires_at,
            ))

    await db.commit()
    await db.refresh(proposal)
    return proposal


async def get_active_bans(db: AsyncSession, community_id: int) -> list[Ban]:
    from datetime import datetime, timezone
    result = await db.execute(
        select(Ban).where(Ban.community_id == community_id)
    )
    bans = result.scalars().all()
    now = datetime.now(timezone.utc)
    return [b for b in bans if b.is_permanent or (b.expires_at and b.expires_at > now)]


# --- Moderator promotion ---

async def propose_mod_promotion(
    db: AsyncSession,
    community_id: int,
    proposed_by_id: int,
    target_user_id: int,
) -> ModProposal:
    mod_count = await _mod_count(db, community_id)
    required = max(2, math.ceil(mod_count / 2))

    proposal = ModProposal(
        community_id=community_id,
        target_user_id=target_user_id,
        proposed_by_id=proposed_by_id,
        vote_count=1,  # proposer's vote counts
        required_votes=required,
    )
    db.add(proposal)
    await db.flush()

    db.add(ModProposalVote(proposal_id=proposal.id, voter_id=proposed_by_id))
    await db.commit()
    await db.refresh(proposal)
    return proposal


async def vote_mod_proposal(
    db: AsyncSession, proposal: ModProposal, voter_id: int
) -> ModProposal:
    """Vote on a mod promotion. Auto-promotes when threshold is reached."""
    # required_votes is locked at proposal creation — do not recalculate here
    proposal.vote_count += 1
    db.add(ModProposalVote(proposal_id=proposal.id, voter_id=voter_id))

    if proposal.vote_count >= proposal.required_votes:
        proposal.status = "approved"
        result = await db.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == proposal.community_id,
                CommunityMember.user_id == proposal.target_user_id,
            )
        )
        member = result.scalar_one_or_none()
        if member:
            member.is_moderator = True

    await db.commit()
    await db.refresh(proposal)
    return proposal
