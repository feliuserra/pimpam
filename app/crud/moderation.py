import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import CommunityMember
from app.models.community_karma import CommunityKarma
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
from app.models.post import Post
from app.schemas.moderation import BanProposalCreate, ModProposalCreate

ROLE_HIERARCHY = {"member": 0, "trusted_member": 1, "moderator": 2, "senior_mod": 3, "owner": 4}
MOD_KARMA_REQUIRED = {"moderator": 200, "senior_mod": 500}
APPEAL_COOLDOWN = timedelta(days=7)


# --- Role helpers ---

async def _get_role(db: AsyncSession, community_id: int, user_id: int) -> str:
    result = await db.execute(
        select(CommunityMember.role).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() or "member"


async def _has_min_role(db: AsyncSession, community_id: int, user_id: int, min_role: str) -> bool:
    role = await _get_role(db, community_id, user_id)
    return ROLE_HIERARCHY.get(role, 0) >= ROLE_HIERARCHY.get(min_role, 0)


async def _is_moderator(db: AsyncSession, community_id: int, user_id: int) -> bool:
    """Backward-compat: True for moderator, senior_mod, and owner."""
    return await _has_min_role(db, community_id, user_id, "moderator")


async def _mod_count(db: AsyncSession, community_id: int) -> int:
    result = await db.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.role.in_(["moderator", "senior_mod", "owner"]),
        )
    )
    return len(result.scalars().all())


async def _is_banned(db: AsyncSession, community_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(Ban).where(
            Ban.community_id == community_id,
            Ban.user_id == user_id,
            Ban.status == "active",
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
    from app.crud.notification import notify
    await notify(db, post.author_id, "post_removed", actor_id=moderator_id, post_id=post.id)
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
        vote_count=1,
        required_votes=10,
    )
    db.add(proposal)
    await db.flush()
    db.add(BanProposalVote(proposal_id=proposal.id, voter_id=proposed_by_id))
    await db.commit()
    await db.refresh(proposal)
    from app.crud.notification import notify
    await notify(db, target_user_id, "ban_proposed", community_id=community_id)
    return proposal


async def vote_ban_proposal(
    db: AsyncSession, proposal: BanProposal, voter_id: int
) -> BanProposal:
    """Cast a vote on a ban proposal. Auto-applies the ban when threshold is reached."""
    proposal.vote_count += 1
    db.add(BanProposalVote(proposal_id=proposal.id, voter_id=voter_id))

    banned_now = False
    if proposal.vote_count >= proposal.required_votes:
        proposal.status = "approved"
        existing = await db.execute(
            select(Ban).where(
                Ban.community_id == proposal.community_id,
                Ban.user_id == proposal.target_user_id,
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(Ban(
                community_id=proposal.community_id,
                user_id=proposal.target_user_id,
                reason=proposal.reason,
                coc_violation=proposal.coc_violation,
                is_permanent=proposal.is_permanent,
                expires_at=proposal.expires_at,
                proposal_id=proposal.id,
            ))
            banned_now = True

    await db.commit()
    await db.refresh(proposal)
    if banned_now:
        from app.crud.notification import notify
        await notify(db, proposal.target_user_id, "banned", community_id=proposal.community_id)
    return proposal


async def get_active_bans(db: AsyncSession, community_id: int) -> list[Ban]:
    result = await db.execute(
        select(Ban).where(Ban.community_id == community_id, Ban.status == "active")
    )
    bans = result.scalars().all()
    now = datetime.now(timezone.utc)
    return [b for b in bans if b.is_permanent or (b.expires_at and b.expires_at > now)]


# --- Ban appeals ---

async def submit_ban_appeal(
    db: AsyncSession, ban_id: int, appellant_id: int, reason: str
) -> BanAppeal:
    """
    Submit an appeal for a ban. Enforces 1-week cooldown and no concurrent pending appeals.
    Raises ValueError with a code string on violation.
    """
    ban_result = await db.execute(
        select(Ban).where(Ban.id == ban_id, Ban.user_id == appellant_id, Ban.status == "active")
    )
    if ban_result.scalar_one_or_none() is None:
        raise ValueError("ban_not_found")

    now = datetime.now(timezone.utc)

    # Check no pending appeal
    pending_result = await db.execute(
        select(BanAppeal).where(BanAppeal.ban_id == ban_id, BanAppeal.status == "pending")
    )
    if pending_result.scalar_one_or_none():
        raise ValueError("pending_appeal_exists")

    # Check cooldown — find last appeal by this user for this ban
    last_result = await db.execute(
        select(BanAppeal)
        .where(BanAppeal.ban_id == ban_id, BanAppeal.appellant_id == appellant_id)
        .order_by(BanAppeal.created_at.desc())
        .limit(1)
    )
    last = last_result.scalar_one_or_none()
    if last:
        last_created = (
            last.created_at.replace(tzinfo=timezone.utc)
            if last.created_at.tzinfo is None
            else last.created_at
        )
        if now - last_created < APPEAL_COOLDOWN:
            raise ValueError("appeal_cooldown")

    appeal = BanAppeal(ban_id=ban_id, appellant_id=appellant_id, reason=reason)
    db.add(appeal)
    await db.commit()
    await db.refresh(appeal)
    return appeal


async def vote_ban_appeal(
    db: AsyncSession, appeal: BanAppeal, voter_id: int
) -> BanAppeal:
    """
    Cast a vote on a ban appeal. Voter must not have voted on the original ban proposal.
    Auto-overturns the ban when threshold is reached.
    Raises ValueError if the voter cast the original ban vote.
    """
    ban_result = await db.execute(select(Ban).where(Ban.id == appeal.ban_id))
    ban = ban_result.scalar_one_or_none()
    if ban and ban.proposal_id:
        orig_vote = await db.execute(
            select(BanProposalVote).where(
                BanProposalVote.proposal_id == ban.proposal_id,
                BanProposalVote.voter_id == voter_id,
            )
        )
        if orig_vote.scalar_one_or_none():
            raise ValueError("voted_on_original_ban")

    appeal.vote_count += 1
    db.add(BanAppealVote(appeal_id=appeal.id, voter_id=voter_id))

    resolved_now = False
    if appeal.vote_count >= appeal.required_votes:
        appeal.status = "approved"
        resolved_now = True
        if ban:
            ban.status = "overturned"

    await db.commit()
    await db.refresh(appeal)
    if resolved_now:
        from app.crud.notification import notify
        community_id = ban.community_id if ban else None
        await notify(db, appeal.appellant_id, "appeal_resolved", community_id=community_id)
    return appeal


async def get_pending_appeals(db: AsyncSession, community_id: int) -> list[BanAppeal]:
    """Return pending appeals for bans in this community."""
    result = await db.execute(
        select(BanAppeal)
        .join(Ban, Ban.id == BanAppeal.ban_id)
        .where(Ban.community_id == community_id, BanAppeal.status == "pending")
    )
    return list(result.scalars().all())


# --- Moderator promotion ---

async def propose_mod_promotion(
    db: AsyncSession,
    community_id: int,
    proposed_by_id: int,
    target_user_id: int,
    data: ModProposalCreate,
) -> ModProposal:
    # Validate target_role
    if data.target_role not in ("moderator", "senior_mod"):
        raise ValueError("invalid_target_role")

    # Check target community karma meets threshold
    karma_result = await db.execute(
        select(CommunityKarma).where(
            CommunityKarma.user_id == target_user_id,
            CommunityKarma.community_id == community_id,
        )
    )
    ck = karma_result.scalar_one_or_none()
    karma = ck.karma if ck else 0
    required_karma = MOD_KARMA_REQUIRED[data.target_role]
    if karma < required_karma:
        raise ValueError(f"insufficient_karma:{required_karma}")

    mod_count = await _mod_count(db, community_id)
    required = max(2, math.ceil(mod_count / 2))

    proposal = ModProposal(
        community_id=community_id,
        target_user_id=target_user_id,
        proposed_by_id=proposed_by_id,
        vote_count=1,
        required_votes=required,
        target_role=data.target_role,
    )
    db.add(proposal)
    await db.flush()
    db.add(ModProposalVote(proposal_id=proposal.id, voter_id=proposed_by_id))
    await db.commit()
    await db.refresh(proposal)
    from app.crud.notification import notify
    await notify(db, target_user_id, "mod_nominated", community_id=community_id)
    return proposal


async def vote_mod_proposal(
    db: AsyncSession, proposal: ModProposal, voter_id: int
) -> ModProposal:
    """Vote on a mod promotion. Auto-promotes when threshold is reached."""
    proposal.vote_count += 1
    db.add(ModProposalVote(proposal_id=proposal.id, voter_id=voter_id))

    promoted_now = False
    if proposal.vote_count >= proposal.required_votes:
        proposal.status = "approved"
        promoted_now = True
        result = await db.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == proposal.community_id,
                CommunityMember.user_id == proposal.target_user_id,
            )
        )
        member = result.scalar_one_or_none()
        if member:
            member.role = proposal.target_role

    await db.commit()
    await db.refresh(proposal)
    if promoted_now:
        from app.crud.notification import notify
        await notify(
            db, proposal.target_user_id, "mod_promoted",
            community_id=proposal.community_id,
        )
    return proposal


# --- Ownership transfer ---

async def propose_ownership_transfer(
    db: AsyncSession, community_id: int, proposed_by_id: int, recipient_id: int
) -> OwnershipTransfer:
    """
    Propose transferring community ownership. Cancels any existing pending transfer.
    """
    existing_result = await db.execute(
        select(OwnershipTransfer).where(
            OwnershipTransfer.community_id == community_id,
            OwnershipTransfer.status == "pending",
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        existing.status = "rejected"

    transfer = OwnershipTransfer(
        community_id=community_id,
        proposed_by_id=proposed_by_id,
        recipient_id=recipient_id,
    )
    db.add(transfer)
    await db.commit()
    await db.refresh(transfer)
    from app.crud.notification import notify
    await notify(db, recipient_id, "ownership_offered", community_id=community_id)
    return transfer


async def respond_to_ownership_transfer(
    db: AsyncSession, transfer: OwnershipTransfer, accept: bool
) -> OwnershipTransfer:
    """Accept or reject an ownership transfer. On accept, updates roles and Community.owner_id."""
    if accept:
        transfer.status = "accepted"

        from app.models.community import Community
        community_result = await db.execute(
            select(Community).where(Community.id == transfer.community_id)
        )
        community = community_result.scalar_one_or_none()

        if community:
            # Downgrade old owner to moderator
            old_owner_result = await db.execute(
                select(CommunityMember).where(
                    CommunityMember.community_id == transfer.community_id,
                    CommunityMember.user_id == community.owner_id,
                )
            )
            old_owner_member = old_owner_result.scalar_one_or_none()
            if old_owner_member:
                old_owner_member.role = "moderator"

            # Update community ownership
            community.owner_id = transfer.recipient_id

            # Promote recipient to owner
            recipient_result = await db.execute(
                select(CommunityMember).where(
                    CommunityMember.community_id == transfer.community_id,
                    CommunityMember.user_id == transfer.recipient_id,
                )
            )
            recipient_member = recipient_result.scalar_one_or_none()
            if recipient_member:
                recipient_member.role = "owner"
            else:
                # Recipient is not yet a member — add them as owner
                db.add(CommunityMember(
                    community_id=transfer.community_id,
                    user_id=transfer.recipient_id,
                    role="owner",
                ))
                community.member_count += 1
    else:
        transfer.status = "rejected"

    await db.commit()
    await db.refresh(transfer)
    return transfer
