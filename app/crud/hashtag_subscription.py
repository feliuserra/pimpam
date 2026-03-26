from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hashtag import Hashtag
from app.models.hashtag_subscription import HashtagSubscription


async def subscribe(
    db: AsyncSession, user_id: int, hashtag_id: int
) -> HashtagSubscription:
    existing = await db.execute(
        select(HashtagSubscription).where(
            HashtagSubscription.user_id == user_id,
            HashtagSubscription.hashtag_id == hashtag_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Already subscribed")

    sub = HashtagSubscription(user_id=user_id, hashtag_id=hashtag_id)
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


async def unsubscribe(db: AsyncSession, user_id: int, hashtag_id: int) -> None:
    result = await db.execute(
        delete(HashtagSubscription).where(
            HashtagSubscription.user_id == user_id,
            HashtagSubscription.hashtag_id == hashtag_id,
        )
    )
    if result.rowcount == 0:
        raise ValueError("Not subscribed")
    await db.commit()


async def get_user_subscriptions(
    db: AsyncSession, user_id: int
) -> list[tuple[HashtagSubscription, Hashtag]]:
    result = await db.execute(
        select(HashtagSubscription, Hashtag)
        .join(Hashtag, HashtagSubscription.hashtag_id == Hashtag.id)
        .where(HashtagSubscription.user_id == user_id)
        .order_by(HashtagSubscription.subscribed_at.desc())
    )
    return list(result.all())


async def get_subscribed_hashtag_ids(db: AsyncSession, user_id: int) -> set[int]:
    result = await db.execute(
        select(HashtagSubscription.hashtag_id).where(
            HashtagSubscription.user_id == user_id
        )
    )
    return set(result.scalars().all())


async def is_subscribed(db: AsyncSession, user_id: int, hashtag_id: int) -> bool:
    result = await db.execute(
        select(HashtagSubscription.id).where(
            HashtagSubscription.user_id == user_id,
            HashtagSubscription.hashtag_id == hashtag_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def get_subscriber_count(db: AsyncSession, hashtag_id: int) -> int:
    result = await db.execute(
        select(func.count()).where(HashtagSubscription.hashtag_id == hashtag_id)
    )
    return result.scalar_one()
