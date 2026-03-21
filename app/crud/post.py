from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.follow import Follow
from app.models.post import Post
from app.schemas.post import PostCreate


async def create_post(db: AsyncSession, data: PostCreate, author_id: int) -> Post:
    post = Post(**data.model_dump(), author_id=author_id)
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def get_post(db: AsyncSession, post_id: int) -> Post | None:
    result = await db.execute(select(Post).where(Post.id == post_id))
    return result.scalar_one_or_none()


async def get_chronological_feed(
    db: AsyncSession,
    user_id: int,
    limit: int = 20,
    before_id: int | None = None,
) -> list[Post]:
    """
    Returns posts from users the given user follows, newest first.
    Uses cursor-based pagination (before_id) — never offset-based.
    No ranking, no ML, no algorithmic ordering. Chronological only.
    """
    followed_ids = select(Follow.followed_id).where(Follow.follower_id == user_id)

    query = (
        select(Post)
        .where(Post.author_id.in_(followed_ids))
        .order_by(Post.created_at.desc())
        .limit(limit)
    )
    if before_id is not None:
        subq = select(Post.created_at).where(Post.id == before_id).scalar_subquery()
        query = query.where(Post.created_at < subq)

    result = await db.execute(query)
    return list(result.scalars().all())


async def delete_post(db: AsyncSession, post: Post) -> None:
    await db.delete(post)
    await db.commit()
