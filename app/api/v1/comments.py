"""
Comment and reaction endpoints.

POST   /posts/{post_id}/comments              — create a comment or reply
GET    /posts/{post_id}/comments              — list top-level comments
GET    /comments/{comment_id}/replies         — list replies to a comment
DELETE /comments/{comment_id}                 — author soft-deletes own comment
POST   /comments/{comment_id}/reactions       — add a reaction
DELETE /comments/{comment_id}/reactions/{rt}  — remove a reaction
"""

import logging
from enum import Enum

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.dependencies import CurrentUser, DBSession, OptionalUser
from app.core.limiter import limiter
from app.core.redis import publish_to_user
from app.crud.comment import (
    create_comment,
    get_comment,
    get_comment_replies,
    get_post_comments,
    get_reaction_counts_batch,
    get_reply_counts_batch,
    get_user_reactions_batch,
    get_watchers,
    soft_delete_comment,
)
from app.crud.comment_reaction import (
    activate_disagrees_for_user,
    add_reaction,
    remove_reaction,
)
from app.crud.post import get_post
from app.schemas.comment import CommentCreate, CommentPublic, ReactionCreate

logger = logging.getLogger("pimpam.comments")

# Two routers so we can use both /posts and /comments prefixes cleanly
post_comments_router = APIRouter(prefix="/posts", tags=["comments"])
comments_router = APIRouter(prefix="/comments", tags=["comments"])


class CommentSort(str, Enum):
    latest = "latest"
    top = "top"


def _comment_to_public(
    comment,
    reaction_counts: dict,
    reply_count: int,
    author_info: tuple[str | None, str | None] = (None, None),
    user_reaction: str | None = None,
) -> CommentPublic:
    return CommentPublic(
        id=comment.id,
        post_id=comment.post_id,
        author_id=comment.author_id,
        author_username=author_info[0],
        author_avatar_url=author_info[1],
        parent_id=comment.parent_id,
        depth=comment.depth,
        content=comment.content if not comment.is_removed else "[deleted]",
        is_removed=comment.is_removed,
        created_at=comment.created_at,
        reaction_counts=reaction_counts,
        reply_count=reply_count,
        user_reaction=user_reaction,
    )


async def _batch_author_info(
    db,
    comments: list,
) -> dict[int, tuple[str | None, str | None]]:
    """Batch-fetch (username, avatar_url) for all comment authors, with signed URLs."""
    from sqlalchemy import select

    from app.core.media_urls import resolve_urls
    from app.models.user import User

    author_ids = {c.author_id for c in comments if c.author_id is not None}
    if not author_ids:
        return {}
    rows = await db.execute(
        select(User.id, User.username, User.avatar_url).where(User.id.in_(author_ids))
    )
    raw = list(rows)
    avatar_keys = [r.avatar_url for r in raw]
    resolved = await resolve_urls(avatar_keys)
    return {r.id: (r.username, resolved[i]) for i, r in enumerate(raw)}


@post_comments_router.post(
    "/{post_id}/comments",
    response_model=CommentPublic,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("1/30 seconds")
async def create(
    request: Request,
    post_id: int,
    data: CommentCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Create a comment on a post, or reply to another comment (via parent_id).
    Maximum nesting depth is 5 levels. Comments cannot be edited after posting.
    """
    post = await get_post(db, post_id)
    if post is None or post.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")

    try:
        comment = await create_comment(db, post_id, current_user.id, data)
    except ValueError as e:
        err = str(e)
        if err == "parent_not_found":
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Parent comment not found"
            )
        if err == "max_depth_exceeded":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Maximum comment depth reached"
            )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=err)

    # If this is a reply, activate any pending 'disagree' the user has on the parent
    if data.parent_id is not None:
        await activate_disagrees_for_user(db, data.parent_id, current_user.id)

    # Persistent notifications
    try:
        from app.crud.comment import get_comment as _get_comment
        from app.crud.notification import notify

        if data.parent_id is not None:
            parent = await _get_comment(db, data.parent_id)
            if parent and parent.author_id != current_user.id:
                await notify(
                    db,
                    parent.author_id,
                    "reply",
                    actor_id=current_user.id,
                    post_id=post_id,
                    comment_id=comment.id,
                )
        # new_comment for the post author (skip if they're the one commenting)
        if post.author_id != current_user.id:
            await notify(
                db,
                post.author_id,
                "new_comment",
                actor_id=current_user.id,
                post_id=post_id,
                comment_id=comment.id,
                group_key=f"comment:post:{post_id}",
            )
    except Exception:
        logger.exception("Failed to send comment notification for post %s", post_id)

    # Notify all watchers (post author + everyone who commented), excluding the commenter
    watchers = await get_watchers(db, post_id, exclude_user_id=current_user.id)
    for watcher_id in watchers:
        await publish_to_user(
            watcher_id,
            "new_comment",
            {
                "post_id": post_id,
                "comment_id": comment.id,
                "author": current_user.username,
                "parent_id": comment.parent_id,
            },
        )

    from app.core.media_urls import resolve_url

    resolved_avatar = await resolve_url(current_user.avatar_url)
    return _comment_to_public(comment, {}, 0, (current_user.username, resolved_avatar))


@post_comments_router.get("/{post_id}/comments", response_model=list[CommentPublic])
async def list_comments(
    post_id: int,
    db: DBSession,
    current_user: OptionalUser = None,
    sort: CommentSort = Query(default=CommentSort.latest),
    limit: int = Query(default=50, le=100),
    before_id: int | None = Query(default=None),
):
    """
    List top-level comments on a post. Use GET /comments/{id}/replies for nested replies.
    Removed comments are included with content replaced by [deleted].
    """
    post = await get_post(db, post_id)
    if post is None or post.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")

    comments = await get_post_comments(
        db, post_id, sort=sort.value, limit=limit, before_id=before_id
    )

    if not comments:
        return []

    ids = [c.id for c in comments]
    reaction_counts = await get_reaction_counts_batch(db, ids)
    reply_counts = await get_reply_counts_batch(db, ids)
    authors = await _batch_author_info(db, comments)
    user_reactions = (
        await get_user_reactions_batch(db, current_user.id, ids) if current_user else {}
    )

    return [
        _comment_to_public(
            c,
            reaction_counts.get(c.id, {}),
            reply_counts.get(c.id, 0),
            authors.get(c.author_id, (None, None)),
            user_reactions.get(c.id),
        )
        for c in comments
    ]


@comments_router.get("/{comment_id}/replies", response_model=list[CommentPublic])
async def list_replies(
    comment_id: int, db: DBSession, current_user: OptionalUser = None
):
    """List direct replies to a comment, oldest first."""
    comment = await get_comment(db, comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found")

    replies = await get_comment_replies(db, comment_id)

    if not replies:
        return []

    ids = [r.id for r in replies]
    reaction_counts = await get_reaction_counts_batch(db, ids)
    reply_counts = await get_reply_counts_batch(db, ids)
    authors = await _batch_author_info(db, replies)
    user_reactions = (
        await get_user_reactions_batch(db, current_user.id, ids) if current_user else {}
    )

    return [
        _comment_to_public(
            r,
            reaction_counts.get(r.id, {}),
            reply_counts.get(r.id, 0),
            authors.get(r.author_id, (None, None)),
            user_reactions.get(r.id),
        )
        for r in replies
    ]


@comments_router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: int, current_user: CurrentUser, db: DBSession):
    """Soft-delete your own comment. The slot remains in the thread shown as [deleted]."""
    comment = await get_comment(db, comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found")
    if comment.author_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your comment")
    if comment.is_removed:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Comment already removed")
    await soft_delete_comment(db, comment)


@comments_router.post("/{comment_id}/reactions", status_code=status.HTTP_204_NO_CONTENT)
async def react(
    comment_id: int, data: ReactionCreate, current_user: CurrentUser, db: DBSession
):
    """
    Add a reaction to a comment (agree, disagree, love, misleading).
    Multiple reaction types are allowed per comment.
    'disagree' is inactive until you also reply to the comment, and is rate-limited to 10/day.
    """
    comment = await get_comment(db, comment_id)
    if comment is None or comment.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found")
    if comment.author_id == current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Cannot react to your own comment"
        )

    try:
        await add_reaction(db, comment_id, current_user.id, data.reaction_type)
    except ValueError as e:
        err = str(e)
        if err == "already_reacted":
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="Already reacted with this type"
            )
        if err == "disagree_limit_reached":
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily disagree limit reached"
            )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=err)


@comments_router.delete(
    "/{comment_id}/reactions/{reaction_type}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_react(
    comment_id: int, reaction_type: str, current_user: CurrentUser, db: DBSession
):
    """Remove a previously cast reaction from a comment."""
    comment = await get_comment(db, comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found")

    try:
        await remove_reaction(db, comment_id, current_user.id, reaction_type)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Reaction not found")
