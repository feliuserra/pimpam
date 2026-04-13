from enum import Enum

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.dependencies import CurrentUser, DBSession, OptionalUser
from app.core.limiter import limiter
from app.core.search import index_community
from app.crud.community import (
    create_community,
    get_community_by_name,
    join_community,
    leave_community,
)
from app.crud.post import annotate_posts_with_user_vote, get_community_posts
from app.schemas.community import (
    CommunityAuditPublic,
    CommunityCreate,
    CommunityKarmaPublic,
    CommunityPublic,
    CommunityUpdate,
)
from app.schemas.post import PostPublic

router = APIRouter(prefix="/communities", tags=["communities"])


async def _resolve_community_urls(
    communities: list[CommunityPublic],
) -> list[CommunityPublic]:
    """Resolve avatar_url S3 keys to signed URLs for a list of communities."""
    from app.core.media_urls import resolve_urls

    keys = [c.avatar_url for c in communities]
    resolved = await resolve_urls(keys)
    return [
        c.model_copy(update={"avatar_url": resolved[i]})
        for i, c in enumerate(communities)
    ]


class SortBy(str, Enum):
    popular = "popular"  # most members first
    alphabetical = "alphabetical"
    newest = "newest"  # most recently created first


@router.get("", response_model=list[CommunityPublic])
async def list_communities(
    db: DBSession,
    sort: SortBy = Query(default=SortBy.popular),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, le=200),
    q: str | None = Query(default=None, max_length=100),
):
    """
    List all communities.

    Sort options:
    - **popular** — most members first (default)
    - **alphabetical** — A to Z
    - **newest** — most recently created first

    Optional **q** parameter filters by name (case-insensitive contains).
    """
    from sqlalchemy import func, select

    from app.models.community import Community

    offset = (page - 1) * limit
    order = {
        SortBy.popular: Community.member_count.desc(),
        SortBy.alphabetical: Community.name.asc(),
        SortBy.newest: Community.created_at.desc(),
    }[sort]

    query = select(Community)
    if q:
        query = query.where(func.lower(Community.name).contains(q.lower()))
    query = query.order_by(order).offset(offset).limit(limit)

    result = await db.execute(query)
    items = [
        CommunityPublic.model_validate(c, from_attributes=True)
        for c in result.scalars().all()
    ]
    return await _resolve_community_urls(items)


@router.get("/joined", response_model=list[CommunityPublic])
async def list_joined(current_user: CurrentUser, db: DBSession):
    """Return communities the authenticated user has joined, with their role."""
    from sqlalchemy import select

    from app.models.community import Community, CommunityMember

    result = await db.execute(
        select(Community, CommunityMember.role)
        .join(CommunityMember, CommunityMember.community_id == Community.id)
        .where(CommunityMember.user_id == current_user.id)
        .order_by(Community.name.asc())
    )
    communities = []
    for community, role in result.all():
        c = CommunityPublic.model_validate(community)
        c.user_role = role
        communities.append(c)
    return await _resolve_community_urls(communities)


@router.post("", response_model=CommunityPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create(
    request: Request, data: CommunityCreate, current_user: CurrentUser, db: DBSession
):
    """Create a new community. The creator becomes owner and first moderator."""
    if await get_community_by_name(db, data.name):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Community name already taken"
        )
    community = await create_community(db, data, owner_id=current_user.id)
    await index_community(community)
    result_pub = CommunityPublic.model_validate(community, from_attributes=True)
    resolved = await _resolve_community_urls([result_pub])
    return resolved[0]


@router.get("/{name}", response_model=CommunityPublic)
async def get(name: str, db: DBSession, current_user: OptionalUser = None):
    """Fetch a community by name."""
    community = await get_community_by_name(db, name)
    if community is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Community not found")
    result_pub = CommunityPublic.model_validate(community)
    if current_user:
        from app.crud.community import get_membership

        membership = await get_membership(db, community.id, current_user.id)
        if membership:
            result_pub.user_role = membership.role
    resolved = await _resolve_community_urls([result_pub])
    return resolved[0]


@router.patch("/{name}", response_model=CommunityPublic)
async def update_community(
    name: str, body: CommunityUpdate, db: DBSession, current_user: CurrentUser
):
    """Moderator+ or admin can update community description and avatar."""
    from app.crud.community import get_membership
    from app.models.community_audit import CommunityAuditLog

    community = await get_community_by_name(db, name)
    if community is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Community not found")

    # Check if user is moderator+ or admin
    is_admin = getattr(current_user, "is_admin", False)
    membership = (
        await get_membership(db, community.id, current_user.id)
        if not is_admin
        else None
    )
    allowed_roles = {"moderator", "senior_mod", "owner"}
    if not is_admin and (not membership or membership.role not in allowed_roles):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Only moderators and above can update this community",
        )

    changes = []
    if body.description is not None:
        community.description = body.description
        changes.append("updated description")
    if body.avatar_url is not None:
        community.avatar_url = body.avatar_url
        changes.append("changed community picture")

    # Log audit entry
    if changes:
        log_entry = CommunityAuditLog(
            community_id=community.id,
            actor_id=current_user.id,
            action="community_update",
            detail=", ".join(changes),
        )
        db.add(log_entry)

    await db.commit()
    await db.refresh(community)
    result_pub = CommunityPublic.model_validate(community, from_attributes=True)
    resolved = await _resolve_community_urls([result_pub])
    return resolved[0]


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
                CommunityMember.role.in_(["moderator", "senior_mod", "owner"]),
            )
        )
        is_mod = result.scalar_one_or_none() is not None

    posts = await get_community_posts(
        db, community.id, limit=limit, before_id=before_id, include_removed=is_mod
    )
    user_id = current_user.id if current_user else None
    return await annotate_posts_with_user_vote(db, posts, user_id)


@router.post("/{name}/join", status_code=status.HTTP_204_NO_CONTENT)
async def join(name: str, current_user: CurrentUser, db: DBSession):
    """Join a community."""
    community = await get_community_by_name(db, name)
    if community is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Community not found")
    try:
        await join_community(db, community, current_user.id)
    except ValueError as exc:
        if str(exc) == "banned":
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="You are banned from this community",
            )
        raise


@router.post("/{name}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave(name: str, current_user: CurrentUser, db: DBSession):
    """Leave a community."""
    community = await get_community_by_name(db, name)
    if community is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Community not found")
    if community.owner_id == current_user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Community owner cannot leave. Transfer ownership first.",
        )
    await leave_community(db, community, current_user.id)


@router.get("/{name}/members/{username}/karma", response_model=CommunityKarmaPublic)
async def get_member_karma(name: str, username: str, db: DBSession):
    """
    Return a member's karma score and role within a community.

    Karma is accumulated when other members vote on the user's posts in this community.
    Members are automatically promoted to ``trusted_member`` once they reach
    50 karma points.
    """
    from sqlalchemy import select

    from app.crud.community_karma import get_community_karma
    from app.crud.user import get_user_by_username
    from app.models.community import CommunityMember

    community = await get_community_by_name(db, name)
    if community is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Community not found")

    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    result = await db.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community.id,
            CommunityMember.user_id == user.id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="User is not a member of this community"
        )

    karma = await get_community_karma(db, user.id, community.id)
    return CommunityKarmaPublic(
        community_id=community.id,
        user_id=user.id,
        karma=karma,
        role=member.role,
    )


@router.get("/{name}/audit-log", response_model=list[CommunityAuditPublic])
async def get_audit_log(
    name: str,
    db: DBSession,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Public audit log of community changes."""
    from sqlalchemy import select

    from app.crud.user import get_user_by_id
    from app.models.community_audit import CommunityAuditLog

    community = await get_community_by_name(db, name)
    if community is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Community not found")

    result = await db.execute(
        select(CommunityAuditLog)
        .where(CommunityAuditLog.community_id == community.id)
        .order_by(CommunityAuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    entries = result.scalars().all()

    out = []
    for entry in entries:
        author = await get_user_by_id(db, entry.actor_id)
        out.append(
            CommunityAuditPublic(
                id=entry.id,
                community_id=entry.community_id,
                actor_id=entry.actor_id,
                actor_username=author.username if author else "deleted",
                action=entry.action,
                detail=entry.detail,
                created_at=entry.created_at,
            )
        )
    return out
