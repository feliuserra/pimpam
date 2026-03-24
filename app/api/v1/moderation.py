"""
Community moderation endpoints.

Role hierarchy: member < trusted_member < moderator < senior_mod < owner

Permission matrix:
  - Vote on ban proposals: trusted_member+
  - Remove/restore posts: moderator+
  - Propose bans: moderator+
  - Vote on ban appeals: moderator+
  - Promote mods: senior_mod+
  - Vote on mod proposals: senior_mod+
  - Propose/accept ownership transfer: senior_mod+
"""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DBSession
from app.crud.community import get_community_by_name
from app.crud.comment import get_comment, mod_remove_comment, mod_restore_comment
from app.crud.moderation import (
    _has_min_role,
    _is_moderator,
    get_active_bans,
    get_pending_appeals,
    propose_ban,
    propose_mod_promotion,
    propose_ownership_transfer,
    remove_post,
    respond_to_ownership_transfer,
    restore_post,
    submit_ban_appeal,
    vote_ban_appeal,
    vote_ban_proposal,
    vote_mod_proposal,
)
from app.crud.post import get_post
from app.crud.user import get_user_by_username
from app.models.moderation import (
    BanAppeal,
    BanAppealVote,
    BanProposal,
    BanProposalVote,
    Ban,
    ModProposal,
    ModProposalVote,
    OwnershipTransfer,
)
from app.schemas.moderation import (
    BanAppealCreate,
    BanAppealPublic,
    BanProposalCreate,
    BanProposalPublic,
    BanPublic,
    ModProposalCreate,
    ModProposalPublic,
    OwnershipTransferCreate,
    OwnershipTransferPublic,
    OwnershipTransferResponse,
)

router = APIRouter(prefix="/communities", tags=["moderation"])


async def _require_mod(db: DBSession, community_id: int, user_id: int):
    if not await _is_moderator(db, community_id, user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Moderator access required")


async def _require_min_role(db: DBSession, community_id: int, user_id: int, min_role: str):
    if not await _has_min_role(db, community_id, user_id, min_role):
        label = min_role.replace("_", " ").title()
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f"{label} access required")


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


@router.delete("/{name}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def mod_remove_comment_endpoint(
    name: str, comment_id: int, current_user: CurrentUser, db: DBSession
):
    """
    Hide a comment from public view. Reversible. Requires moderator+ role.
    The comment slot remains in the thread shown as [removed by moderator].
    """
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)

    comment = await get_comment(db, comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found")

    # Ensure the comment belongs to a post in this community
    from sqlalchemy import select
    from app.models.post import Post
    post_result = await db.execute(select(Post).where(Post.id == comment.post_id))
    post = post_result.scalar_one_or_none()
    if post is None or post.community_id != community.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found in this community")

    await mod_remove_comment(db, comment, moderator_id=current_user.id)


@router.post("/{name}/comments/{comment_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def mod_restore_comment_endpoint(
    name: str, comment_id: int, current_user: CurrentUser, db: DBSession
):
    """Restore a previously removed comment. Requires moderator+ role."""
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)

    comment = await get_comment(db, comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found")

    from sqlalchemy import select
    from app.models.post import Post
    post_result = await db.execute(select(Post).where(Post.id == comment.post_id))
    post = post_result.scalar_one_or_none()
    if post is None or post.community_id != community.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found in this community")

    await mod_restore_comment(db, comment)


# --- Bans ---

@router.post("/{name}/bans", response_model=BanProposalPublic, status_code=status.HTTP_201_CREATED)
async def propose_ban_endpoint(
    name: str, data: BanProposalCreate, current_user: CurrentUser, db: DBSession
):
    """
    Propose banning a user from this community.
    Requires a Code of Conduct violation reason.
    The proposal needs 10 votes to take effect.
    The proposer's vote is counted automatically.
    Requires moderator+ role.
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
    Requires trusted_member+ role. When 10 votes are reached, the ban is applied automatically.
    """
    community = await _get_community_or_404(db, name)
    await _require_min_role(db, community.id, current_user.id, "trusted_member")

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


# --- Ban appeals ---

@router.post("/{name}/appeals", response_model=BanAppealPublic, status_code=status.HTTP_201_CREATED)
async def submit_appeal(
    name: str, data: BanAppealCreate, current_user: CurrentUser, db: DBSession
):
    """Submit an appeal for your ban from this community. 1-week cooldown between appeals."""
    # Community must exist, but the ban check is inside submit_ban_appeal
    await _get_community_or_404(db, name)

    error_map = {
        "ban_not_found": (404, "No active ban found for your account"),
        "pending_appeal_exists": (409, "A pending appeal already exists for this ban"),
        "appeal_cooldown": (429, "Must wait 1 week between appeals"),
    }
    try:
        return await submit_ban_appeal(db, data.ban_id, current_user.id, data.reason)
    except ValueError as e:
        code, msg = error_map.get(str(e), (400, str(e)))
        raise HTTPException(code, detail=msg)


@router.post("/{name}/appeals/{appeal_id}/vote", response_model=BanAppealPublic)
async def vote_appeal(
    name: str, appeal_id: int, current_user: CurrentUser, db: DBSession
):
    """
    Vote to overturn a ban appeal.
    Requires moderator+ and must not have voted on the original ban.
    """
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)

    result = await db.execute(
        select(BanAppeal)
        .join(Ban, Ban.id == BanAppeal.ban_id)
        .where(
            BanAppeal.id == appeal_id,
            Ban.community_id == community.id,
            BanAppeal.status == "pending",
        )
    )
    appeal = result.scalar_one_or_none()
    if appeal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Appeal not found or already resolved")

    already = await db.execute(
        select(BanAppealVote).where(
            BanAppealVote.appeal_id == appeal_id,
            BanAppealVote.voter_id == current_user.id,
        )
    )
    if already.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Already voted on this appeal")

    try:
        return await vote_ban_appeal(db, appeal, current_user.id)
    except ValueError as e:
        if str(e) == "voted_on_original_ban":
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Cannot vote on appeal for a ban you voted on",
            )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{name}/appeals", response_model=list[BanAppealPublic])
async def list_appeals(name: str, current_user: CurrentUser, db: DBSession):
    """List pending ban appeals in this community. Moderators only."""
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)
    return await get_pending_appeals(db, community.id)


# --- Moderator promotion ---

@router.post("/{name}/moderators", response_model=ModProposalPublic, status_code=status.HTTP_201_CREATED)
async def propose_mod_endpoint(
    name: str, data: ModProposalCreate, current_user: CurrentUser, db: DBSession
):
    """
    Propose promoting a community member to moderator or senior_mod.
    Requires senior_mod+ role.
    Target must have 200+ community karma for moderator, 500+ for senior_mod.
    The proposer's vote is counted automatically.
    """
    community = await _get_community_or_404(db, name)
    await _require_min_role(db, community.id, current_user.id, "senior_mod")

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

    try:
        return await propose_mod_promotion(db, community.id, current_user.id, target.id, data)
    except ValueError as e:
        err = str(e)
        if err == "invalid_target_role":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="target_role must be 'moderator' or 'senior_mod'")
        if err.startswith("insufficient_karma:"):
            required = err.split(":")[1]
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Target user needs at least {required} community karma",
            )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=err)


@router.post("/{name}/moderators/{proposal_id}/vote", response_model=ModProposalPublic)
async def vote_mod_endpoint(
    name: str, proposal_id: int, current_user: CurrentUser, db: DBSession
):
    """
    Vote in favour of a mod promotion proposal.
    Requires senior_mod+ role. When a majority agree, the member is promoted automatically.
    """
    community = await _get_community_or_404(db, name)
    await _require_min_role(db, community.id, current_user.id, "senior_mod")

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


# --- Ownership transfer ---

@router.post(
    "/{name}/ownership-transfer",
    response_model=OwnershipTransferPublic,
    status_code=status.HTTP_201_CREATED,
)
async def propose_transfer(
    name: str, data: OwnershipTransferCreate, current_user: CurrentUser, db: DBSession
):
    """Propose transferring community ownership to another member. Requires senior_mod+."""
    community = await _get_community_or_404(db, name)
    await _require_min_role(db, community.id, current_user.id, "senior_mod")

    recipient = await get_user_by_username(db, data.recipient_username)
    if recipient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    if recipient.id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot transfer ownership to yourself")

    return await propose_ownership_transfer(db, community.id, current_user.id, recipient.id)


@router.post(
    "/{name}/ownership-transfer/{transfer_id}/respond",
    response_model=OwnershipTransferPublic,
)
async def respond_transfer(
    name: str,
    transfer_id: int,
    data: OwnershipTransferResponse,
    current_user: CurrentUser,
    db: DBSession,
):
    """Accept or reject an ownership transfer proposal. Only the designated recipient can respond."""
    community = await _get_community_or_404(db, name)

    result = await db.execute(
        select(OwnershipTransfer).where(
            OwnershipTransfer.id == transfer_id,
            OwnershipTransfer.community_id == community.id,
            OwnershipTransfer.status == "pending",
        )
    )
    transfer = result.scalar_one_or_none()
    if transfer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Transfer not found or already resolved")
    if transfer.recipient_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only the designated recipient can respond")

    return await respond_to_ownership_transfer(db, transfer, data.accept)
