import logging

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select

from app.core.config import settings  # noqa: F401 (used in delete endpoint)
from app.core.dependencies import (
    CurrentUser,
    DBSession,
    OptionalUser,
    UnverifiedCurrentUser,
)
from app.core.limiter import limiter
from app.core.search import index_user
from app.core.security import verify_password
from app.crud.account_deletion import cancel_deletion, schedule_deletion
from app.crud.post import get_user_posts
from app.crud.user import (
    check_is_following,
    get_follower_count,
    get_followers,
    get_following,
    get_following_count,
    get_user_by_username,
    get_user_data_export,
)
from app.federation.actor import actor_id, build_follow, build_undo_follow
from app.federation.delivery import deliver_activity
from app.models.follow import Follow
from app.schemas.post import PostPublic
from app.schemas.user import DeleteAccountRequest, UserPublic, UserUpdate

logger = logging.getLogger("pimpam.users")

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: UnverifiedCurrentUser, db: DBSession):
    """Return the authenticated user's own profile, including verification, deletion status, and follower counts."""
    fc = await get_follower_count(db, current_user.id)
    fing = await get_following_count(db, current_user.id)
    return UserPublic.model_validate(current_user, from_attributes=True).model_copy(
        update={"follower_count": fc, "following_count": fing}
    )


@router.patch("/me", response_model=UserPublic)
async def update_me(
    data: UserUpdate, current_user: UnverifiedCurrentUser, db: DBSession
):
    """Update the authenticated user's profile fields."""
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    await index_user(current_user)
    fc = await get_follower_count(db, current_user.id)
    fing = await get_following_count(db, current_user.id)
    return UserPublic.model_validate(current_user, from_attributes=True).model_copy(
        update={"follower_count": fc, "following_count": fing}
    )


@router.get("/{username}", response_model=UserPublic)
async def get_user(username: str, db: DBSession, current_user: OptionalUser = None):
    """
    Fetch a public user profile by username.
    Includes follower/following counts and, when authenticated, an ``is_following`` flag.
    """
    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    fc = await get_follower_count(db, user.id)
    fing = await get_following_count(db, user.id)
    is_following = None
    if current_user is not None and current_user.id != user.id:
        is_following = await check_is_following(db, current_user.id, user.id)
    return UserPublic.model_validate(user, from_attributes=True).model_copy(
        update={
            "follower_count": fc,
            "following_count": fing,
            "is_following": is_following,
        }
    )


@router.get("/{username}/followers", response_model=list[UserPublic])
async def list_followers(
    username: str,
    db: DBSession,
    limit: int = Query(default=50, le=200),
):
    """Return the list of confirmed followers for a user, newest first."""
    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return await get_followers(db, user.id, limit=limit)


@router.get("/{username}/following", response_model=list[UserPublic])
async def list_following(
    username: str,
    db: DBSession,
    limit: int = Query(default=50, le=200),
):
    """Return the list of users that this user is confirmed following, newest first."""
    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return await get_following(db, user.id, limit=limit)


@router.get("/{username}/posts", response_model=list[PostPublic])
async def list_user_posts(
    username: str,
    db: DBSession,
    current_user: OptionalUser = None,
    limit: int = Query(default=20, le=100),
    before_id: int | None = Query(default=None),
):
    """Return public, non-removed posts by this user, newest first. Cursor-paginated via ``before_id``."""
    from app.crud.post import annotate_posts_with_user_vote

    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    posts = await get_user_posts(db, user.id, limit=limit, before_id=before_id)
    user_id = current_user.id if current_user else None
    return await annotate_posts_with_user_vote(db, posts, user_id)


@router.post("/{username}/follow", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def follow(
    request: Request, username: str, current_user: CurrentUser, db: DBSession
):
    """
    Follow a user. For remote (federated) users, sends an AP Follow activity and
    marks the follow as pending until the remote server sends an Accept.
    """
    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cannot follow yourself"
        )

    existing = await db.execute(
        select(Follow).where(
            Follow.follower_id == current_user.id, Follow.followed_id == user.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Already following this user"
        )

    # Remote follows are pending until the remote server sends Accept
    is_pending = user.is_remote and settings.federation_enabled
    db.add(
        Follow(follower_id=current_user.id, followed_id=user.id, is_pending=is_pending)
    )
    await db.commit()

    # Notify the followed user (local only — remote users have their own notification system)
    if not user.is_remote:
        try:
            from app.crud.notification import notify

            await notify(db, user.id, "follow", actor_id=current_user.id)
        except Exception:
            logger.exception("Failed to send follow notification to user %s", user.id)

    if is_pending and user.ap_inbox:
        activity = build_follow(
            current_user.username,
            actor_id(user.username) if not user.ap_id else user.ap_id,
        )
        try:
            await deliver_activity(activity, current_user, [user.ap_inbox])
        except Exception:
            logger.exception("Failed to deliver AP Follow to %s", user.ap_inbox)


@router.delete("/{username}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow(username: str, current_user: CurrentUser, db: DBSession):
    """
    Unfollow a user. For remote (federated) users, sends an AP Undo{Follow} activity.
    """
    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    result = await db.execute(
        select(Follow).where(
            Follow.follower_id == current_user.id, Follow.followed_id == user.id
        )
    )
    follow = result.scalar_one_or_none()
    if follow is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not following this user")

    await db.delete(follow)
    await db.commit()

    if user.is_remote and settings.federation_enabled and user.ap_inbox:
        followed_ap_id = user.ap_id or actor_id(user.username)
        activity = build_undo_follow(current_user.username, followed_ap_id)
        try:
            await deliver_activity(activity, current_user, [user.ap_inbox])
        except Exception:
            logger.exception("Failed to deliver AP Undo{Follow} to %s", user.ap_inbox)


# ---------------------------------------------------------------------------
# GDPR data export
# ---------------------------------------------------------------------------


@router.get("/me/data-export")
@limiter.limit("3/hour")
async def data_export(request: Request, current_user: CurrentUser, db: DBSession):
    """
    Export all personal data for the authenticated user as a JSON archive.

    Includes profile, posts, comments, messages, follows, community karma, and consent log.
    Rate-limited to 3 requests per hour. Triggers a file download in the browser.
    """
    data = await get_user_data_export(db, current_user.id)
    from fastapi.responses import JSONResponse

    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="pimpam-export-{current_user.username}.json"'
        },
    )


# ---------------------------------------------------------------------------
# Account deletion
# ---------------------------------------------------------------------------


@router.delete("/me", status_code=status.HTTP_202_ACCEPTED)
async def delete_me(
    data: DeleteAccountRequest, current_user: UnverifiedCurrentUser, db: DBSession
):
    """
    Schedule the authenticated account for permanent deletion (alias for ``POST /users/me/delete``).

    Behaves identically to ``POST /users/me/delete`` — account is soft-deleted and hard-deleted
    after a 7-day grace period. Use ``POST /users/me/delete/cancel`` to undo within the window.
    """
    if not verify_password(data.password, current_user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    if current_user.deletion_scheduled_at is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Deletion already scheduled"
        )
    await schedule_deletion(db, current_user)
    return {
        "detail": f"Account scheduled for deletion in {settings.account_deletion_grace_days} days"
    }


@router.post("/me/delete", status_code=status.HTTP_202_ACCEPTED)
async def request_deletion(
    data: DeleteAccountRequest, current_user: UnverifiedCurrentUser, db: DBSession
):
    """
    Schedule the authenticated account for permanent deletion.

    The account will be hard-deleted after a 7-day grace period. During that
    window the account continues to work normally and deletion can be cancelled
    via ``POST /users/me/delete/cancel``.

    All posts and comments will be anonymised (shown as "[deleted user]").
    Direct messages you sent will be anonymised; the other party keeps them.
    Everything else (votes, reactions, follows, notifications) is purged.

    Requires your current password to confirm intent.
    Returns ``409`` if deletion is already scheduled.
    """
    if not verify_password(data.password, current_user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    if current_user.deletion_scheduled_at is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Deletion already scheduled"
        )
    await schedule_deletion(db, current_user)
    return {
        "detail": f"Account scheduled for deletion in {settings.account_deletion_grace_days} days"
    }


@router.post("/me/delete/cancel", status_code=status.HTTP_200_OK)
async def cancel_deletion_request(current_user: UnverifiedCurrentUser, db: DBSession):
    """
    Cancel a pending account deletion.

    Returns ``400`` if no deletion was scheduled.
    """
    if current_user.deletion_scheduled_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No deletion scheduled")
    await cancel_deletion(db, current_user)
    return {"detail": "Deletion cancelled"}
