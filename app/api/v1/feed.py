from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query, Request
from sqlalchemy import func, select

from app.core.dependencies import CurrentUser, DBSession, OptionalUser
from app.core.limiter import limiter
from app.crud.post import annotate_posts_with_user_vote, get_chronological_feed
from app.models.comment import Comment
from app.models.community import Community
from app.models.post import Post
from app.schemas.post import PostPublic

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("", response_model=list[PostPublic])
@limiter.limit("60/minute")
async def get_feed(
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
    limit: int = Query(default=20, le=50),
    before_id: int | None = Query(default=None),
):
    """
    Chronological feed of posts from users you follow.
    Cursor-based pagination via before_id.
    No ranking. No algorithms. No ML.
    """
    posts = await get_chronological_feed(
        db, current_user.id, limit=limit, before_id=before_id
    )
    return await annotate_posts_with_user_vote(db, posts, current_user.id)


@router.get("/trending", response_model=list[PostPublic])
@limiter.limit("60/minute")
async def get_trending(
    request: Request,
    db: DBSession,
    current_user: OptionalUser,
    limit: int = Query(default=15, le=30),
    hours: int = Query(default=24, le=168),
):
    """
    Top posts by engagement score in the last N hours.

    Score = karma + 2 × comment_count. Transparent, non-personalised,
    capped at `limit` posts. This is opt-in discovery, not an algorithmic feed.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    comment_count_sub = (
        select(Comment.post_id, func.count().label("cc"))
        .where(Comment.is_removed == False)  # noqa: E712
        .group_by(Comment.post_id)
        .subquery()
    )

    score = (Post.karma + 2 * func.coalesce(comment_count_sub.c.cc, 0)).label("score")

    query = (
        select(Post)
        .outerjoin(comment_count_sub, comment_count_sub.c.post_id == Post.id)
        .where(
            Post.created_at >= cutoff,
            Post.is_removed == False,  # noqa: E712
            Post.visibility == "public",
        )
        .order_by(score.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    posts = list(result.scalars().all())
    user_id = current_user.id if current_user else None
    return await annotate_posts_with_user_vote(db, posts, user_id)


@router.get("/news", response_model=list[PostPublic])
@limiter.limit("60/minute")
async def get_news(
    request: Request,
    db: DBSession,
    current_user: OptionalUser,
    limit: int = Query(default=20, le=50),
    before_id: int | None = Query(default=None),
):
    """
    Chronological posts from communities tagged as news.

    No editorial layer — just an aggregated feed from is_news communities,
    newest first, cursor-paginated.
    """
    news_community_ids = select(Community.id).where(
        Community.is_news == True  # noqa: E712
    )

    query = (
        select(Post)
        .where(
            Post.community_id.in_(news_community_ids),
            Post.is_removed == False,  # noqa: E712
            Post.visibility == "public",
        )
        .order_by(Post.created_at.desc())
        .limit(limit)
    )

    if before_id is not None:
        subq = select(Post.created_at).where(Post.id == before_id).scalar_subquery()
        query = query.where(Post.created_at < subq)

    result = await db.execute(query)
    posts = list(result.scalars().all())
    user_id = current_user.id if current_user else None
    return await annotate_posts_with_user_vote(db, posts, user_id)


@router.get("/for-you", response_model=list[PostPublic])
@limiter.limit("60/minute")
async def get_for_you(
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
    limit: int = Query(default=20, le=50),
    before_id: int | None = Query(default=None),
):
    """
    Personalised discover feed based on explicit interest signals.

    Shows posts that match hashtags you subscribe to, or posts picked by
    moderators in communities you've joined. Strictly chronological — no
    scoring, no weighting. Every post includes attribution explaining why
    it appeared.

    Formula: posts matching subscribed hashtags OR picked in joined communities,
    ordered by created_at DESC. Reproducible with a spreadsheet.
    """
    from app.crud.discover_feed import get_for_you_feed

    items = await get_for_you_feed(
        db, current_user.id, limit=limit, before_id=before_id
    )
    if not items:
        return []

    posts = [item["post"] for item in items]
    annotated = await annotate_posts_with_user_vote(db, posts, current_user.id)

    # Attach attribution to each annotated post
    for post_public, item in zip(annotated, items):
        post_public.attribution = item["attribution"]

    return annotated
