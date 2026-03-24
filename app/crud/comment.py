from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import MAX_DEPTH, Comment, CommentReaction
from app.schemas.comment import CommentCreate


async def get_comment(db: AsyncSession, comment_id: int) -> Comment | None:
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    return result.scalar_one_or_none()


async def create_comment(
    db: AsyncSession,
    post_id: int,
    author_id: int,
    data: CommentCreate,
) -> Comment:
    """
    Create a top-level comment or a reply.
    Raises ValueError for invalid parent or max depth exceeded.
    """
    depth = 0
    if data.parent_id is not None:
        parent = await get_comment(db, data.parent_id)
        if parent is None or parent.post_id != post_id:
            raise ValueError("parent_not_found")
        if parent.depth >= MAX_DEPTH:
            raise ValueError("max_depth_exceeded")
        depth = parent.depth + 1

    comment = Comment(
        post_id=post_id,
        author_id=author_id,
        parent_id=data.parent_id,
        depth=depth,
        content=data.content,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


async def get_post_comments(
    db: AsyncSession,
    post_id: int,
    sort: str = "latest",
    limit: int = 50,
    before_id: int | None = None,
) -> list[Comment]:
    """
    Return top-level comments for a post (parent_id IS NULL).
    sort='latest' — newest first; sort='top' — highest positive-reaction count first.
    Replies are fetched separately via get_comment_replies.
    Removed comments are included (shown as [deleted] by the client).
    """
    query = select(Comment).where(
        Comment.post_id == post_id,
        Comment.parent_id.is_(None),
    )

    if before_id is not None and sort == "latest":
        subq = select(Comment.created_at).where(Comment.id == before_id).scalar_subquery()
        query = query.where(Comment.created_at < subq)

    if sort == "top":
        # Order by count of positive reactions (agree + love), then newest
        positive_types = ("agree", "love")
        pos_count = (
            select(func.count(CommentReaction.id))
            .where(
                CommentReaction.comment_id == Comment.id,
                CommentReaction.reaction_type.in_(positive_types),
                CommentReaction.activated == True,  # noqa: E712
            )
            .correlate(Comment)
            .scalar_subquery()
        )
        query = query.order_by(pos_count.desc(), Comment.created_at.desc())
    else:
        query = query.order_by(Comment.created_at.desc())

    query = query.limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_comment_replies(db: AsyncSession, comment_id: int) -> list[Comment]:
    """Return direct replies to a comment, oldest first."""
    result = await db.execute(
        select(Comment)
        .where(Comment.parent_id == comment_id)
        .order_by(Comment.created_at.asc())
    )
    return list(result.scalars().all())


async def soft_delete_comment(db: AsyncSession, comment: Comment) -> None:
    """Author's own deletion — soft delete, content replaced by client with [deleted]."""
    comment.is_removed = True
    await db.commit()


async def mod_remove_comment(db: AsyncSession, comment: Comment, moderator_id: int) -> None:
    comment.is_removed = True
    comment.removed_by_id = moderator_id
    await db.commit()
    from app.crud.notification import notify
    await notify(
        db, comment.author_id, "comment_removed",
        actor_id=moderator_id, comment_id=comment.id, post_id=comment.post_id,
    )


async def mod_restore_comment(db: AsyncSession, comment: Comment) -> None:
    comment.is_removed = False
    comment.removed_by_id = None
    await db.commit()


async def get_reaction_counts(db: AsyncSession, comment_id: int) -> dict[str, int]:
    """Return a dict of reaction_type → count for active reactions on a comment."""
    result = await db.execute(
        select(CommentReaction.reaction_type, func.count(CommentReaction.id))
        .where(
            CommentReaction.comment_id == comment_id,
            CommentReaction.activated == True,  # noqa: E712
        )
        .group_by(CommentReaction.reaction_type)
    )
    return {row[0]: row[1] for row in result.all()}


async def get_reaction_counts_batch(
    db: AsyncSession, comment_ids: list[int]
) -> dict[int, dict[str, int]]:
    """
    Fetch active reaction counts for multiple comments in a single query.
    Returns {comment_id: {reaction_type: count}}.
    """
    if not comment_ids:
        return {}
    result = await db.execute(
        select(
            CommentReaction.comment_id,
            CommentReaction.reaction_type,
            func.count(CommentReaction.id).label("cnt"),
        )
        .where(
            CommentReaction.comment_id.in_(comment_ids),
            CommentReaction.activated == True,  # noqa: E712
        )
        .group_by(CommentReaction.comment_id, CommentReaction.reaction_type)
    )
    counts: dict[int, dict[str, int]] = {cid: {} for cid in comment_ids}
    for comment_id, reaction_type, cnt in result.all():
        counts[comment_id][reaction_type] = cnt
    return counts


async def get_reply_count(db: AsyncSession, comment_id: int) -> int:
    result = await db.execute(
        select(func.count(Comment.id)).where(Comment.parent_id == comment_id)
    )
    return result.scalar_one()


async def get_reply_counts_batch(
    db: AsyncSession, comment_ids: list[int]
) -> dict[int, int]:
    """
    Fetch reply counts for multiple comments in a single query.
    Returns {comment_id: reply_count}.
    """
    if not comment_ids:
        return {}
    result = await db.execute(
        select(Comment.parent_id, func.count(Comment.id).label("cnt"))
        .where(Comment.parent_id.in_(comment_ids))
        .group_by(Comment.parent_id)
    )
    counts = {cid: 0 for cid in comment_ids}
    for parent_id, cnt in result.all():
        counts[parent_id] = cnt
    return counts


async def get_watchers(db: AsyncSession, post_id: int, exclude_user_id: int) -> list[int]:
    """
    Return user IDs of the post author + everyone who has commented on the post,
    excluding the given user (the one triggering the notification).
    """
    from app.models.post import Post

    author_result = await db.execute(
        select(Post.author_id).where(Post.id == post_id)
    )
    author_id = author_result.scalar_one_or_none()

    commenters_result = await db.execute(
        select(Comment.author_id)
        .where(Comment.post_id == post_id)
        .distinct()
    )
    watcher_ids = set(commenters_result.scalars().all())
    if author_id is not None:
        watcher_ids.add(author_id)
    watcher_ids.discard(exclude_user_id)
    return list(watcher_ids)
