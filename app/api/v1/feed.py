from fastapi import APIRouter, Query, Request

from app.core.dependencies import CurrentUser, DBSession
from app.core.limiter import limiter
from app.crud.post import get_chronological_feed
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
    return await get_chronological_feed(db, current_user.id, limit=limit, before_id=before_id)
