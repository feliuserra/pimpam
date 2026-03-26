"""
Hashtag endpoints.

GET    /hashtags/trending               — trending hashtags by post count
GET    /hashtags/subscriptions          — user's subscribed hashtags
GET    /hashtags/{name}                 — get a single hashtag
GET    /hashtags/{name}/posts           — posts tagged with a hashtag
POST   /hashtags/{name}/subscribe       — subscribe to a hashtag
DELETE /hashtags/{name}/subscribe       — unsubscribe from a hashtag
"""

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.dependencies import CurrentUser, DBSession, OptionalUser
from app.core.limiter import limiter
from app.crud.hashtag import (
    get_hashtag_by_name,
    get_post_ids_for_hashtag,
    get_trending_hashtags,
)
from app.crud.hashtag_subscription import (
    get_subscriber_count,
    get_user_subscriptions,
    is_subscribed,
    subscribe,
    unsubscribe,
)
from app.crud.post import annotate_posts_with_user_vote, get_post
from app.schemas.hashtag import HashtagPublic
from app.schemas.hashtag_subscription import HashtagSubscriptionPublic
from app.schemas.post import PostPublic

router = APIRouter(prefix="/hashtags", tags=["hashtags"])


@router.get("/trending", response_model=list[HashtagPublic])
async def trending(
    db: DBSession,
    limit: int = Query(20, ge=1, le=50),
):
    """Return trending hashtags ordered by post count."""
    return await get_trending_hashtags(db, limit)


@router.get("/subscriptions", response_model=list[HashtagSubscriptionPublic])
async def list_subscriptions(current_user: CurrentUser, db: DBSession):
    """Return the hashtags the current user subscribes to."""
    rows = await get_user_subscriptions(db, current_user.id)
    return [
        HashtagSubscriptionPublic(
            id=sub.id,
            hashtag_id=sub.hashtag_id,
            hashtag_name=tag.name,
            subscribed_at=sub.subscribed_at,
        )
        for sub, tag in rows
    ]


@router.get("/{name}", response_model=HashtagPublic)
async def get_hashtag(name: str, db: DBSession, current_user: OptionalUser = None):
    """Get a hashtag by name, with subscription status for authenticated users."""
    tag = await get_hashtag_by_name(db, name)
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Hashtag not found")

    sub_count = await get_subscriber_count(db, tag.id)
    user_subscribed = False
    if current_user:
        user_subscribed = await is_subscribed(db, current_user.id, tag.id)

    return HashtagPublic.model_validate(tag, from_attributes=True).model_copy(
        update={
            "subscriber_count": sub_count,
            "is_subscribed": user_subscribed,
        }
    )


@router.get("/{name}/posts", response_model=list[PostPublic])
async def posts_by_hashtag(
    name: str,
    db: DBSession,
    current_user: OptionalUser = None,
    limit: int = Query(20, ge=1, le=50),
    before_id: int | None = Query(None),
):
    """List posts tagged with a given hashtag, newest first."""
    tag = await get_hashtag_by_name(db, name)
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Hashtag not found")

    post_ids = await get_post_ids_for_hashtag(db, tag.id, limit, before_id)
    if not post_ids:
        return []

    posts = []
    for pid in post_ids:
        p = await get_post(db, pid)
        if p and not p.is_removed:
            posts.append(p)

    user_id = current_user.id if current_user else None
    return await annotate_posts_with_user_vote(db, posts, user_id)


@router.post("/{name}/subscribe", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def subscribe_to_hashtag(
    name: str, request: Request, current_user: CurrentUser, db: DBSession
):
    """Subscribe to a hashtag to see matching posts in your For You feed."""
    tag = await get_hashtag_by_name(db, name)
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Hashtag not found")

    try:
        await subscribe(db, current_user.id, tag.id)
    except ValueError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Already subscribed")

    return {"detail": "Subscribed"}


@router.delete("/{name}/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_from_hashtag(name: str, current_user: CurrentUser, db: DBSession):
    """Unsubscribe from a hashtag."""
    tag = await get_hashtag_by_name(db, name)
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Hashtag not found")

    try:
        await unsubscribe(db, current_user.id, tag.id)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not subscribed")
