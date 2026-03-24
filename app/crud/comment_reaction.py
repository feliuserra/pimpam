from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.comment import Comment, CommentReaction


async def add_reaction(
    db: AsyncSession,
    comment_id: int,
    user_id: int,
    reaction_type: str,
) -> CommentReaction:
    """
    Add a reaction to a comment.

    Rules:
    - Each (comment, user, reaction_type) pair is unique — duplicate raises ValueError.
    - 'disagree' starts as inactive (activated=False); it activates automatically when the
      user leaves a reply on the same comment (handled in create_comment).
    - 'disagree' is rate-limited to settings.disagree_daily_limit per user per day.
    - Karma effect is applied immediately for activated reactions.

    Raises ValueError('already_reacted'), ValueError('disagree_limit_reached').
    """
    # Check for duplicate
    existing = await db.execute(
        select(CommentReaction).where(
            CommentReaction.comment_id == comment_id,
            CommentReaction.user_id == user_id,
            CommentReaction.reaction_type == reaction_type,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError("already_reacted")

    # Rate-limit disagrees
    if reaction_type == "disagree":
        since = datetime.now(timezone.utc) - timedelta(days=1)
        count_result = await db.execute(
            select(func.count(CommentReaction.id)).where(
                CommentReaction.user_id == user_id,
                CommentReaction.reaction_type == "disagree",
                CommentReaction.created_at >= since,
            )
        )
        if count_result.scalar_one() >= settings.disagree_daily_limit:
            raise ValueError("disagree_limit_reached")

    # disagree starts inactive until an accompanying reply is left
    activated = reaction_type != "disagree"

    reaction = CommentReaction(
        comment_id=comment_id,
        user_id=user_id,
        reaction_type=reaction_type,
        activated=activated,
    )
    db.add(reaction)

    # Apply karma for immediately-activated reactions
    if activated:
        karma_delta = settings.reaction_karma.get(reaction_type, 0)
        if karma_delta != 0:
            await _apply_reaction_karma(db, comment_id, karma_delta)

    await db.commit()
    await db.refresh(reaction)

    # Notify comment author (grouped by comment)
    from app.crud.notification import notify
    comment_result = await db.execute(
        select(Comment).where(Comment.id == comment_id)
    )
    comment = comment_result.scalar_one_or_none()
    if comment:
        await notify(
            db, comment.author_id, "reaction",
            actor_id=user_id, comment_id=comment_id,
            group_key=f"reaction:comment:{comment_id}",
        )

    return reaction


async def remove_reaction(
    db: AsyncSession,
    comment_id: int,
    user_id: int,
    reaction_type: str,
) -> None:
    """
    Remove a reaction. Reverses karma if the reaction was active.
    Raises ValueError('reaction_not_found').
    """
    result = await db.execute(
        select(CommentReaction).where(
            CommentReaction.comment_id == comment_id,
            CommentReaction.user_id == user_id,
            CommentReaction.reaction_type == reaction_type,
        )
    )
    reaction = result.scalar_one_or_none()
    if reaction is None:
        raise ValueError("reaction_not_found")

    if reaction.activated:
        karma_delta = settings.reaction_karma.get(reaction_type, 0)
        if karma_delta != 0:
            await _apply_reaction_karma(db, comment_id, -karma_delta)

    await db.delete(reaction)
    await db.commit()


async def activate_disagrees_for_user(
    db: AsyncSession,
    comment_id: int,
    user_id: int,
) -> None:
    """
    Called when a user leaves a reply on a comment.
    Activates any pending 'disagree' reaction that user has on the parent comment.
    The disagree reaction type has 0 karma effect so no karma adjustment is needed.
    """
    result = await db.execute(
        select(CommentReaction).where(
            CommentReaction.comment_id == comment_id,
            CommentReaction.user_id == user_id,
            CommentReaction.reaction_type == "disagree",
            CommentReaction.activated == False,  # noqa: E712
        )
    )
    reaction = result.scalar_one_or_none()
    if reaction is not None:
        reaction.activated = True
        # disagree karma is 0, so no karma change needed
        await db.commit()


async def _apply_reaction_karma(db: AsyncSession, comment_id: int, karma_delta: int) -> None:
    """Apply karma_delta to the comment author's global karma."""
    comment_result = await db.execute(
        select(Comment).where(Comment.id == comment_id)
    )
    comment = comment_result.scalar_one_or_none()
    if comment is None:
        return

    from app.crud.user import get_user_by_id
    author = await get_user_by_id(db, comment.author_id)
    if author:
        author.karma += karma_delta
