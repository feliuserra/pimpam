from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vote import Vote


async def get_vote(db: AsyncSession, user_id: int, post_id: int) -> Vote | None:
    result = await db.execute(
        select(Vote).where(Vote.user_id == user_id, Vote.post_id == post_id)
    )
    return result.scalar_one_or_none()


async def create_initial_vote(db: AsyncSession, user_id: int, post_id: int) -> Vote:
    """Create the author's automatic +1 vote when a post is created."""
    vote = Vote(user_id=user_id, post_id=post_id, direction=1)
    db.add(vote)
    # No commit — called inside create_post's transaction
    return vote


async def cast_vote(
    db: AsyncSession,
    user_id: int,
    post_id: int,
    direction: int,
) -> tuple[Vote, int]:
    """
    Cast or change a vote. Returns (vote, karma_delta).
    karma_delta is the net change to apply to Post.karma and User.karma.
    Does NOT commit — the caller owns the transaction so karma updates
    on Post and User happen atomically with the vote.
    """
    existing = await get_vote(db, user_id, post_id)

    if existing:
        if existing.direction == direction:
            return existing, 0  # no change
        old_direction = existing.direction
        existing.direction = direction
        return existing, direction - old_direction  # e.g. was -1, now +1 → delta = +2
    else:
        vote = Vote(user_id=user_id, post_id=post_id, direction=direction)
        db.add(vote)
        return vote, direction


async def retract_vote(db: AsyncSession, user_id: int, post_id: int) -> int:
    """
    Remove a vote. Returns the karma_delta (negative of the removed direction).
    Does NOT commit — the caller owns the transaction.
    Raises ValueError if no vote exists.
    """
    vote = await get_vote(db, user_id, post_id)
    if vote is None:
        raise ValueError("No vote to retract")
    delta = -vote.direction
    await db.delete(vote)
    return delta
