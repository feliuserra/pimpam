"""Community karma tracking and trusted-member auto-promotion."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import CommunityMember
from app.models.community_karma import CommunityKarma

TRUSTED_MEMBER_THRESHOLD = 50


async def get_community_karma(db: AsyncSession, user_id: int, community_id: int) -> int:
    result = await db.execute(
        select(CommunityKarma).where(
            CommunityKarma.user_id == user_id,
            CommunityKarma.community_id == community_id,
        )
    )
    ck = result.scalar_one_or_none()
    return ck.karma if ck else 0


async def update_community_karma(
    db: AsyncSession, user_id: int, community_id: int, delta: int
) -> None:
    """
    Adjust community karma and auto-promote/demote trusted_member role.
    No commit — caller owns the transaction.
    """
    result = await db.execute(
        select(CommunityKarma).where(
            CommunityKarma.user_id == user_id,
            CommunityKarma.community_id == community_id,
        )
    )
    ck = result.scalar_one_or_none()
    if ck is None:
        ck = CommunityKarma(user_id=user_id, community_id=community_id, karma=delta)
        db.add(ck)
        new_karma = delta
    else:
        ck.karma += delta
        new_karma = ck.karma

    # Auto-sync trusted_member role
    member_result = await db.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == user_id,
        )
    )
    member = member_result.scalar_one_or_none()
    if member is None:
        return
    if new_karma >= TRUSTED_MEMBER_THRESHOLD and member.role == "member":
        member.role = "trusted_member"
    elif new_karma < TRUSTED_MEMBER_THRESHOLD and member.role == "trusted_member":
        member.role = "member"
    # Never touch moderator, senior_mod, or owner
