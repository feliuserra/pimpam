from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.curated_pick import CuratedPick
from app.models.post import Post

MAX_PICKS_PER_COMMUNITY = 3


async def create_pick(
    db: AsyncSession,
    post_id: int,
    community_id: int,
    curator_id: int,
    note: str | None = None,
) -> CuratedPick:
    count = await count_active_picks(db, community_id)
    if count >= MAX_PICKS_PER_COMMUNITY:
        raise ValueError(f"Maximum {MAX_PICKS_PER_COMMUNITY} picks per community")

    # Check the post isn't already picked
    existing = await db.execute(
        select(CuratedPick).where(
            CuratedPick.post_id == post_id,
            CuratedPick.community_id == community_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Post is already picked")

    pick = CuratedPick(
        post_id=post_id,
        community_id=community_id,
        curator_id=curator_id,
        note=note,
    )
    db.add(pick)
    await db.commit()
    await db.refresh(pick)
    return pick


async def remove_pick(db: AsyncSession, pick_id: int, community_id: int) -> bool:
    result = await db.execute(
        delete(CuratedPick).where(
            CuratedPick.id == pick_id,
            CuratedPick.community_id == community_id,
        )
    )
    await db.commit()
    return result.rowcount > 0


async def get_community_picks(
    db: AsyncSession, community_id: int, limit: int = MAX_PICKS_PER_COMMUNITY
) -> list[tuple[CuratedPick, Post]]:
    result = await db.execute(
        select(CuratedPick, Post)
        .join(Post, CuratedPick.post_id == Post.id)
        .where(
            CuratedPick.community_id == community_id,
            Post.is_removed == False,  # noqa: E712
        )
        .order_by(CuratedPick.created_at.desc())
        .limit(limit)
    )
    return list(result.all())


async def get_picks_for_communities(
    db: AsyncSession,
    community_ids: list[int],
    limit: int = 20,
    before_id: int | None = None,
) -> list[tuple[CuratedPick, Post]]:
    if not community_ids:
        return []

    query = (
        select(CuratedPick, Post)
        .join(Post, CuratedPick.post_id == Post.id)
        .where(
            CuratedPick.community_id.in_(community_ids),
            Post.is_removed == False,  # noqa: E712
            Post.visibility == "public",
        )
        .order_by(CuratedPick.created_at.desc())
        .limit(limit)
    )

    if before_id is not None:
        subq = (
            select(CuratedPick.created_at)
            .where(CuratedPick.id == before_id)
            .scalar_subquery()
        )
        query = query.where(CuratedPick.created_at < subq)

    result = await db.execute(query)
    return list(result.all())


async def count_active_picks(db: AsyncSession, community_id: int) -> int:
    result = await db.execute(
        select(func.count()).where(CuratedPick.community_id == community_id)
    )
    return result.scalar_one()
