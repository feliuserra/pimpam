"""
Community curated picks.

Moderators can surface up to 3 posts per community. Every pick is attributed
to the curator — fully transparent human curation, not algorithmic.

POST   /communities/{name}/picks           — pick a post
DELETE /communities/{name}/picks/{pick_id}  — remove a pick
GET    /communities/{name}/picks            — list active picks
"""

from fastapi import APIRouter, HTTPException, Request, status

from app.core.dependencies import CurrentUser, DBSession, OptionalUser
from app.core.limiter import limiter
from app.crud.community import get_community_by_name
from app.crud.curated_pick import create_pick, get_community_picks, remove_pick
from app.crud.post import annotate_posts_with_user_vote, get_post
from app.schemas.curated_pick import CuratedPickCreate, CuratedPickPublic

router = APIRouter(prefix="/communities", tags=["curated-picks"])


async def _get_community_or_404(db, name):
    community = await get_community_by_name(db, name)
    if not community:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Community not found")
    return community


async def _require_mod(db, community_id, user_id):
    from app.crud.moderation import _is_moderator

    if not await _is_moderator(db, community_id, user_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Moderator access required"
        )


@router.post(
    "/{name}/picks",
    response_model=CuratedPickPublic,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def pick_post(
    name: str,
    body: CuratedPickCreate,
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Pick a post to surface it in the community and in members' For You feeds.
    Moderator or above required. Maximum 3 picks per community.
    """
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)

    post = await get_post(db, body.post_id)
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.community_id != community.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Post does not belong to this community",
        )
    if post.is_removed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cannot pick a removed post"
        )

    try:
        pick = await create_pick(
            db, body.post_id, community.id, current_user.id, body.note
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e))

    return CuratedPickPublic(
        id=pick.id,
        post_id=pick.post_id,
        community_id=pick.community_id,
        community_name=community.name,
        curator_id=pick.curator_id,
        curator_username=current_user.username,
        note=pick.note,
        created_at=pick.created_at,
    )


@router.delete("/{name}/picks/{pick_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unpick_post(
    name: str, pick_id: int, current_user: CurrentUser, db: DBSession
):
    """Remove a curated pick. Moderator or above required."""
    community = await _get_community_or_404(db, name)
    await _require_mod(db, community.id, current_user.id)

    ok = await remove_pick(db, pick_id, community.id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pick not found")


@router.get("/{name}/picks", response_model=list[CuratedPickPublic])
async def list_picks(name: str, db: DBSession, current_user: OptionalUser = None):
    """List active curated picks for a community. Public endpoint."""
    community = await _get_community_or_404(db, name)
    rows = await get_community_picks(db, community.id)

    user_id = current_user.id if current_user else None

    results = []
    for pick, post in rows:
        from sqlalchemy import select

        from app.models.user import User

        curator_row = await db.execute(
            select(User.username).where(User.id == pick.curator_id)
        )
        curator_username = curator_row.scalar_one_or_none() or ""

        post_publics = await annotate_posts_with_user_vote(db, [post], user_id)
        post_public = post_publics[0] if post_publics else None

        results.append(
            CuratedPickPublic(
                id=pick.id,
                post_id=pick.post_id,
                community_id=pick.community_id,
                community_name=community.name,
                curator_id=pick.curator_id,
                curator_username=curator_username,
                note=pick.note,
                created_at=pick.created_at,
                post=post_public,
            )
        )

    return results
