"""
Per-user ActivityPub endpoints:
  GET  /users/{username}          — Actor document
  GET  /users/{username}/inbox    — OrderedCollection stub
  POST /users/{username}/inbox    — Receive activities (signature-verified)
  GET  /users/{username}/outbox   — OrderedCollection of recent posts
  GET  /users/{username}/followers
  GET  /users/{username}/following
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.core.dependencies import DBSession
from app.crud.user import get_user_by_username
from app.federation import activity_handler
from app.federation.actor import (
    actor_id,
    build_actor,
    build_create,
    ordered_collection,
)
from app.federation.constants import AP_CONTENT_TYPES
from app.federation.signatures import verify_inbox_signature
from app.models.follow import Follow
from app.models.post import Post

router = APIRouter(tags=["federation"])

AP_JSON = "application/activity+json"


def _ap_response(data: dict) -> JSONResponse:
    return JSONResponse(content=data, media_type=AP_JSON)


async def _get_local_user_or_404(username: str, db: DBSession):
    user = await get_user_by_username(db, username)
    if user is None or user.is_remote:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/users/{username}")
async def get_actor(username: str, request: Request, db: DBSession):
    """
    Serve the AP Actor document for a local user.
    Browsers get a redirect to the profile page; AP clients get JSON-LD.
    """
    accept = request.headers.get("accept", "")
    if not any(ct in accept for ct in AP_CONTENT_TYPES) and "html" in accept:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=f"https://{request.url.netloc}/@{username}")

    user = await _get_local_user_or_404(username, db)
    return _ap_response(build_actor(user))


@router.get("/users/{username}/inbox")
async def get_inbox(username: str, db: DBSession):
    """Inbox GET — returns an empty OrderedCollection (not used by most AP clients)."""
    await _get_local_user_or_404(username, db)
    base = f"{actor_id(username)}/inbox"
    return _ap_response(ordered_collection(base, [], 0))


@router.post("/users/{username}/inbox", status_code=status.HTTP_202_ACCEPTED)
async def post_inbox(
    username: str,
    request: Request,
    db: DBSession,
    _actor: dict = Depends(verify_inbox_signature),
):
    """
    Receive an ActivityPub activity from a remote server.
    Signature is verified by the dependency before this handler runs.
    Returns 202 Accepted for all valid-signature requests, including unknown types.
    """
    await _get_local_user_or_404(username, db)
    try:
        activity = await request.json()
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body")

    await activity_handler.dispatch(activity, db)
    return {"status": "accepted"}


@router.get("/users/{username}/outbox")
async def get_outbox(username: str, db: DBSession):
    """
    Outbox — serves the user's 20 most recent local posts as Create{Note} activities.
    """
    user = await _get_local_user_or_404(username, db)
    result = await db.execute(
        select(Post)
        .where(Post.author_id == user.id, Post.ap_id == None)  # noqa: E711
        .order_by(Post.created_at.desc())
        .limit(20)
    )
    posts = result.scalars().all()

    count_result = await db.execute(
        select(func.count()).select_from(Post).where(Post.author_id == user.id)
    )
    total = count_result.scalar_one()

    items = [build_create(post, user) for post in posts]
    base = f"{actor_id(username)}/outbox"
    return _ap_response(ordered_collection(base, items, total))


@router.get("/users/{username}/followers")
async def get_followers(username: str, db: DBSession):
    """Return the list of follower actor IDs."""
    user = await _get_local_user_or_404(username, db)
    from app.models.user import User as UserModel
    result = await db.execute(
        select(UserModel.ap_id).join(Follow, Follow.follower_id == UserModel.id).where(
            Follow.followed_id == user.id
        )
    )
    follower_ids = [row[0] for row in result.all() if row[0]]
    count_result = await db.execute(
        select(func.count()).select_from(Follow).where(Follow.followed_id == user.id)
    )
    return _ap_response(ordered_collection(f"{actor_id(username)}/followers", follower_ids, count_result.scalar_one()))


@router.get("/users/{username}/following")
async def get_following(username: str, db: DBSession):
    """Return the list of followed actor IDs."""
    user = await _get_local_user_or_404(username, db)
    from app.models.user import User as UserModel
    result = await db.execute(
        select(UserModel.ap_id).join(Follow, Follow.followed_id == UserModel.id).where(
            Follow.follower_id == user.id
        )
    )
    followed_ids = [row[0] for row in result.all() if row[0]]
    count_result = await db.execute(
        select(func.count()).select_from(Follow).where(Follow.follower_id == user.id)
    )
    return _ap_response(ordered_collection(f"{actor_id(username)}/following", followed_ids, count_result.scalar_one()))
