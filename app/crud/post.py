from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.follow import Follow
from app.models.post import Post
from app.schemas.comment import ShareCreate
from app.schemas.post import PostCreate, PostUpdate

EDIT_WINDOW = timedelta(hours=1)


async def create_post(db: AsyncSession, data: PostCreate, author_id: int) -> Post:
    post = Post(**data.model_dump(), author_id=author_id, karma=1)
    db.add(post)
    await db.flush()  # get post.id before creating the vote

    # Author's implicit +1 — cannot be changed or retracted
    from app.crud.vote import create_initial_vote
    await create_initial_vote(db, user_id=author_id, post_id=post.id)

    await db.commit()
    await db.refresh(post)
    return post


async def get_post(db: AsyncSession, post_id: int) -> Post | None:
    result = await db.execute(select(Post).where(Post.id == post_id))
    return result.scalar_one_or_none()


async def edit_post(db: AsyncSession, post: Post, data: PostUpdate) -> Post:
    """
    Edit a post within the 1-hour edit window.
    Raises ValueError if the window has passed.
    Edit history is intentionally not stored — only the edited flag is public.
    """
    created = post.created_at.replace(tzinfo=timezone.utc) if post.created_at.tzinfo is None else post.created_at
    if datetime.now(timezone.utc) - created > EDIT_WINDOW:
        raise ValueError("Edit window has closed (1 hour after posting)")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(post, field, value)
    post.is_edited = True
    post.edited_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(post)
    return post


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
    Removed posts are excluded from the feed.
    """
    followed_ids = select(Follow.followed_id).where(
        Follow.follower_id == user_id,
        Follow.is_pending == False,  # noqa: E712 — exclude pending federated follows
    )

    query = (
        select(Post)
        .where(Post.author_id.in_(followed_ids), Post.is_removed == False)  # noqa: E712
        .order_by(Post.created_at.desc())
        .limit(limit)
    )
    if before_id is not None:
        subq = select(Post.created_at).where(Post.id == before_id).scalar_subquery()
        query = query.where(Post.created_at < subq)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_community_posts(
    db: AsyncSession,
    community_id: int,
    limit: int = 20,
    before_id: int | None = None,
    include_removed: bool = False,
) -> list[Post]:
    """
    Chronological posts for a community.
    Moderators pass include_removed=True to see hidden posts.
    """
    query = select(Post).where(Post.community_id == community_id)

    if not include_removed:
        query = query.where(Post.is_removed == False)  # noqa: E712

    query = query.order_by(Post.created_at.desc()).limit(limit)

    if before_id is not None:
        subq = select(Post.created_at).where(Post.id == before_id).scalar_subquery()
        query = query.where(Post.created_at < subq)

    result = await db.execute(query)
    return list(result.scalars().all())


async def delete_post(db: AsyncSession, post: Post) -> None:
    await db.delete(post)
    await db.commit()


async def create_share(
    db: AsyncSession,
    original: Post,
    author_id: int,
    data: ShareCreate,
) -> Post:
    """
    Create a share (reshare) of an existing post.
    - Traces through share chains: sharing a share links to the root original.
    - Enforces one share per user per original post.
    Raises ValueError('already_shared') if the user has already shared this post.
    """
    # Trace to root original so shares of shares still point to the root
    root_id = original.shared_from_id if original.shared_from_id is not None else original.id

    existing = await db.execute(
        select(Post).where(
            Post.author_id == author_id,
            Post.shared_from_id == root_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError("already_shared")

    root = await get_post(db, root_id) if root_id != original.id else original

    post = Post(
        title=root.title,
        content=root.content,
        url=root.url,
        image_url=root.image_url,
        author_id=author_id,
        community_id=data.community_id,
        karma=1,
        shared_from_id=root_id,
        share_comment=data.comment,
    )
    db.add(post)
    await db.flush()

    from app.crud.vote import create_initial_vote
    await create_initial_vote(db, user_id=author_id, post_id=post.id)

    await db.commit()
    await db.refresh(post)
    return post
