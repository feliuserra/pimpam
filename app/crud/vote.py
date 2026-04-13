from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.vote import Vote


async def get_vote(db: AsyncSession, user_id: int, post_id: int) -> Vote | None:
    result = await db.execute(
        select(Vote).where(Vote.user_id == user_id, Vote.post_id == post_id)
    )
    return result.scalar_one_or_none()


async def get_user_votes_for_posts(
    db: AsyncSession, user_id: int, post_ids: list[int]
) -> dict[int, int]:
    """Return a mapping of post_id -> vote direction for the given user.

    Only posts the user has voted on are included in the result.
    """
    if not post_ids:
        return {}
    result = await db.execute(
        select(Vote.post_id, Vote.direction).where(
            Vote.user_id == user_id, Vote.post_id.in_(post_ids)
        )
    )
    return dict(result.all())


async def create_initial_vote(db: AsyncSession, user_id: int, post_id: int) -> Vote:
    """Create the author's automatic +1 vote when a post is created."""
    vote = Vote(user_id=user_id, post_id=post_id, direction=1)
    db.add(vote)
    # No commit — called inside create_post's transaction
    return vote


async def _apply_karma(db: AsyncSession, post: Post, karma_delta: int) -> None:
    """Apply karma_delta to the post, its author, and community karma (if applicable)."""
    if karma_delta == 0:
        return

    post.karma += karma_delta

    from app.crud.user import get_user_by_id

    author = await get_user_by_id(db, post.author_id)
    if author:
        author.karma += karma_delta

    # Also credit original post author when a share is voted on
    if post.shared_from_id is not None:
        from app.crud.post import get_post

        original = await get_post(db, post.shared_from_id)
        if original and original.author_id != post.author_id:
            original_author = await get_user_by_id(db, original.author_id)
            if original_author:
                if karma_delta > 0:
                    original_author.karma += 1
                elif karma_delta < 0:
                    original_author.karma -= 1

    if post.community_id is not None:
        from app.crud.community_karma import update_community_karma

        await update_community_karma(db, post.author_id, post.community_id, karma_delta)


async def cast_vote(
    db: AsyncSession,
    user_id: int,
    post: Post,
    direction: int,
) -> Vote:
    """
    Cast or change a vote. Applies karma changes to Post, User, and CommunityKarma
    atomically. Commits the transaction.
    """
    existing = await get_vote(db, user_id, post.id)

    if existing:
        if existing.direction == direction:
            return existing  # no change
        karma_delta = direction - existing.direction
        existing.direction = direction
        vote = existing
    else:
        vote = Vote(user_id=user_id, post_id=post.id, direction=direction)
        db.add(vote)
        karma_delta = direction

    await _apply_karma(db, post, karma_delta)
    await db.commit()
    return vote


async def retract_vote(db: AsyncSession, user_id: int, post: Post) -> None:
    """
    Remove a vote. Applies karma changes and commits.
    Raises ValueError if no vote exists.
    """
    vote = await get_vote(db, user_id, post.id)
    if vote is None:
        raise ValueError("No vote to retract")
    karma_delta = -vote.direction
    await db.delete(vote)
    await _apply_karma(db, post, karma_delta)
    await db.commit()
