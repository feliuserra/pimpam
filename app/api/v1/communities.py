from enum import Enum

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.dependencies import CurrentUser, DBSession, OptionalUser
from app.core.limiter import limiter
from app.crud.community import (
    create_community,
    get_community_by_name,
    join_community,
    leave_community,
)
from app.crud.post import get_community_posts
from app.schemas.community import CommunityCreate, CommunityPublic
from app.schemas.post import PostPublic

router = APIRouter(prefix="/communities", tags=["communities"])


class SortBy(str, Enum):
    popular = "popular"          # most members first
    alphabetical = "alphabetical"
    newest = "newest"            # most recently created first


@router.get("", response_model=list[CommunityPublic])
async def list_communities(
    db: DBSession,
    sort: SortBy = Query(default=SortBy.popular),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, le=50),
):
    """
    List all communities.

    Sort options:
    - **popular** — most members first (default)
    - **alphabetical** — A to Z
    - **newest** — most recently created first
    """
    from sqlalchemy import select
    from app.models.community import Community

    offset = (page - 1) * limit
    order = {
        SortBy.popular: Community.member_count.desc(),
        SortBy.alphabetical: Community.name.asc(),
        SortBy.newest: Community.created_at.desc(),
    }[sort]

    result = await db.execute(select(Community).order_by(order).offset(offset).limit(limit))
    return result.scalars().all()


@router.post("", response_model=CommunityPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create(request: Request, data: CommunityCreate, current_user: CurrentUser, db: DBSession):
    """Create a new community. The creator becomes owner and first moderator."""
    if await get_community_by_name(db, data.name):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Community name already taken")
    return await create_community(db, data, owner_id=current_user.id)


@router.get("/{name}", response_model=CommunityPublic)
async def get(name: str, db: DBSession):
    """Fetch a community by name."""
    community = await get_community_by_name(db, name)
    if community is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Community not found")
    return community


@router.get("/{name}/posts", response_model=list[PostPublic])
async def list_posts(
    name: str,
    db: DBSession,
    current_user: OptionalUser,
    limit: int = Query(default=20, le=50),
    before_id: int | None = Query(default=None),
):
    """
    Chronological posts for a community, newest first.
    Moderators see removed posts (marked with is_removed=True).
    """
    community = await get_community_by_name(db, name)
    if community is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Community not found")

    # Check if current user is a moderator of this community
    is_mod = False
    if current_user:
        from sqlalchemy import select
        from app.models.community import CommunityMember
        result = await db.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community.id,
                CommunityMember.user_id == current_user.id,
                CommunityMember.is_moderator == True,  # noqa: E712
            )
        )
        is_mod = result.scalar_one_or_none() is not None

    return await get_community_posts(
        db, community.id, limit=limit, before_id=before_id, include_removed=is_mod
    )


@router.post("/{name}/join", status_code=status.HTTP_204_NO_CONTENT)
async def join(name: str, current_user: CurrentUser, db: DBSession):
    """Join a community."""
    community = await get_community_by_name(db, name)
    if community is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Community not found")
    await join_community(db, community, current_user.id)


@router.post("/{name}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave(name: str, current_user: CurrentUser, db: DBSession):
    """Leave a community."""
    community = await get_community_by_name(db, name)
    if community is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Community not found")
    await leave_community(db, community, current_user.id)
