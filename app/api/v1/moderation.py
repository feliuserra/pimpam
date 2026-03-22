"""
Community moderation endpoints.
All actions require the requesting user to be a moderator of the community.
"""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DBSession
from app.crud.community import get_community_by_name
from app.crud.moderation import (
    _is_moderator,
    get_active_bans,
    propose_ban,
    propose_mod_promotion,
    remove_post,
    restore_post,
    vote_ban_proposal,
    vote_mod_proposal,
)
from app.crud.post import get_post
from app.crud.user import get_user_by_username
from app.models.moderation import BanProposal, BanProposalVote, ModProposal, ModProposalVote
from app.schemas.moderation import (
    BanProposalCreate,
    BanProposalPublic,
    BanPublic,
    ModProposalCreate,
    ModProposalPublic,
)

router = APIRouter(prefix="/communities", tags=["moderation"])


async def _require_mod(db: DBSession, community_id: int, user_id: int):
    if not await _is_moderator(db, community_id, user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Moderator access required")


async def _get_community_or_404(db: DBSession, name: str):
    community = await get_community_by_name(db, name)
    if community is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Community not found")
    return community


# --- Post removal ---

@router.delete("/{name}/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def mod_remove_post(name: str, post_id: int, current_user: CurrentUser, db: DBSession):
    """
    Hide a post from public view. The post is not deleted — moderators can still see it.
    Only moderators of this community may remove posts.
    """
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)

    post = await get_post(db, post_id)
    if post is None or post.community_id != community.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found in this community")

    await remove_post(db, post, moderator_id=current_user.id)


@router.post("/{name}/posts/{post_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def mod_restore_post(name: str, post_id: int, current_user: CurrentUser, db: DBSession):
    """Restore a previously removed post."""
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)

    post = await get_post(db, post_id)
    if post is None or post.community_id != community.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found in this community")

    await restore_post(db, post)


# --- Bans ---

@router.post("/{name}/bans", response_model=BanProposalPublic, status_code=status.HTTP_201_CREATED)
async def propose_ban_endpoint(
    name: str, data: BanProposalCreate, current_user: CurrentUser, db: DBSession
):
    """
    Propose banning a user from this community.
    Requires a Code of Conduct violation reason.
    The proposal needs 10 moderator votes to take effect.
    The proposer's vote is counted automatically.
    """
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)

    target = await get_user_by_username(db, data.target_username)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Target user not found")
    if target.id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot propose banning yourself")

    return await propose_ban(db, community.id, current_user.id, target.id, data)


@router.post("/{name}/bans/{proposal_id}/vote", response_model=BanProposalPublic)
async def vote_ban_endpoint(
    name: str, proposal_id: int, current_user: CurrentUser, db: DBSession
):
    """
    Vote in favour of a ban proposal.
    Each moderator can vote once. When 10 votes are reached, the ban is applied automatically.
    """
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)

    result = await db.execute(
        select(BanProposal).where(
            BanProposal.id == proposal_id,
            BanProposal.community_id == community.id,
            BanProposal.status == "pending",
        )
    )
    proposal = result.scalar_one_or_none()
    if proposal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ban proposal not found or already resolved")

    already = await db.execute(
        select(BanProposalVote).where(
            BanProposalVote.proposal_id == proposal_id,
            BanProposalVote.voter_id == current_user.id,
        )
    )
    if already.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Already voted on this proposal")

    return await vote_ban_proposal(db, proposal, current_user.id)


@router.get("/{name}/bans", response_model=list[BanPublic])
async def list_bans(name: str, current_user: CurrentUser, db: DBSession):
    """List active bans in this community. Moderators only."""
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)
    return await get_active_bans(db, community.id)


# --- Moderator promotion ---

@router.post("/{name}/moderators", response_model=ModProposalPublic, status_code=status.HTTP_201_CREATED)
async def propose_mod_endpoint(
    name: str, data: ModProposalCreate, current_user: CurrentUser, db: DBSession
):
    """
    Propose promoting a community member to moderator.
    Requires majority of current moderators to agree (minimum 2 votes).
    The proposer's vote is counted automatically.
    """
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)

    target = await get_user_by_username(db, data.target_username)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Target user not found")
    if target.id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot propose yourself")

    # Check target is a member of the community
    from app.models.community import CommunityMember
    membership = await db.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community.id,
            CommunityMember.user_id == target.id,
        )
    )
    if membership.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User is not a member of this community")

    return await propose_mod_promotion(db, community.id, current_user.id, target.id)


@router.post("/{name}/moderators/{proposal_id}/vote", response_model=ModProposalPublic)
async def vote_mod_endpoint(
    name: str, proposal_id: int, current_user: CurrentUser, db: DBSession
):
    """
    Vote in favour of a mod promotion proposal.
    When a majority of moderators agree, the member is promoted automatically.
    """
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)

    result = await db.execute(
        select(ModProposal).where(
            ModProposal.id == proposal_id,
            ModProposal.community_id == community.id,
            ModProposal.status == "pending",
        )
    )
    proposal = result.scalar_one_or_none()
    if proposal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Proposal not found or already resolved")

    already = await db.execute(
        select(ModProposalVote).where(
            ModProposalVote.proposal_id == proposal_id,
            ModProposalVote.voter_id == current_user.id,
        )
    )
    if already.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Already voted on this proposal")

    return await vote_mod_proposal(db, proposal, current_user.id)
