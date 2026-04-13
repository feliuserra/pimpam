from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import Community, CommunityMember
from app.schemas.community import CommunityCreate

_AVATARS = [f"/avatars/dog-{i:02d}.svg" for i in range(1, 21)]


async def get_community_by_name(db: AsyncSession, name: str) -> Community | None:
    result = await db.execute(select(Community).where(Community.name == name))
    return result.scalar_one_or_none()


async def create_community(
    db: AsyncSession, data: CommunityCreate, owner_id: int
) -> Community:
    import random

    community = Community(
        **data.model_dump(), owner_id=owner_id, avatar_url=random.choice(_AVATARS)
    )
    db.add(community)
    await db.flush()  # get the id before adding membership

    # Owner is automatically the community owner-member
    membership = CommunityMember(
        community_id=community.id, user_id=owner_id, role="owner"
    )
    db.add(membership)
    community.member_count = 1
    await db.commit()
    await db.refresh(community)
    return community


async def get_membership(
    db: AsyncSession, community_id: int, user_id: int
) -> CommunityMember | None:
    result = await db.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def is_user_banned(db: AsyncSession, community_id: int, user_id: int) -> bool:
    """Check if a user has an active ban in a community."""
    from datetime import datetime, timezone

    from app.models.moderation import Ban

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
    if ban.expires_at is not None:
        now = datetime.now(timezone.utc)
        expires = ban.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires > now:
            return True
        # Ban has expired — mark it inactive
        ban.status = "expired"
        await db.flush()
        return False
    return True


async def join_community(
    db: AsyncSession, community: Community, user_id: int
) -> CommunityMember:
    if await is_user_banned(db, community.id, user_id):
        raise ValueError("banned")
    existing = await get_membership(db, community.id, user_id)
    if existing:
        return existing
    membership = CommunityMember(community_id=community.id, user_id=user_id)
    db.add(membership)
    community.member_count += 1
    await db.commit()
    return membership


async def leave_community(db: AsyncSession, community: Community, user_id: int) -> None:
    result = await db.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community.id,
            CommunityMember.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership:
        await db.delete(membership)
        community.member_count = max(0, community.member_count - 1)
        await db.commit()
