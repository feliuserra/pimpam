from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import Community, CommunityMember
from app.schemas.community import CommunityCreate


async def get_community_by_name(db: AsyncSession, name: str) -> Community | None:
    result = await db.execute(select(Community).where(Community.name == name))
    return result.scalar_one_or_none()


async def create_community(
    db: AsyncSession, data: CommunityCreate, owner_id: int
) -> Community:
    community = Community(**data.model_dump(), owner_id=owner_id)
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


async def join_community(
    db: AsyncSession, community: Community, user_id: int
) -> CommunityMember:
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
