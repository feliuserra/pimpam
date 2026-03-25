"""
Hashtag endpoints.

GET  /hashtags/trending               — trending hashtags by post count
GET  /hashtags/{name}                 — get a single hashtag
GET  /hashtags/{name}/posts           — posts tagged with a hashtag
"""

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import DBSession, OptionalUser
from app.crud.hashtag import (
    get_hashtag_by_name,
    get_post_ids_for_hashtag,
    get_trending_hashtags,
)
from app.crud.post import annotate_posts_with_user_vote, get_post
from app.schemas.hashtag import HashtagPublic
from app.schemas.post import PostPublic

router = APIRouter(prefix="/hashtags", tags=["hashtags"])


@router.get("/trending", response_model=list[HashtagPublic])
async def trending(
    db: DBSession,
    limit: int = Query(20, ge=1, le=50),
):
    """Return trending hashtags ordered by post count."""
    return await get_trending_hashtags(db, limit)


@router.get("/{name}", response_model=HashtagPublic)
async def get_hashtag(name: str, db: DBSession):
    """Get a hashtag by name."""
    tag = await get_hashtag_by_name(db, name)
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Hashtag not found")
    return tag


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
