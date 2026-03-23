from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.config import settings
from app.core.dependencies import CurrentUser, DBSession
from app.core.limiter import limiter
from app.crud.user import get_user_by_username
from app.federation.actor import actor_id, build_follow, build_undo_follow
from app.federation.delivery import deliver_activity
from app.models.follow import Follow
from app.schemas.user import UserPublic, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

 
@router.get("/me", response_model=UserPublic)
async def get_me(current_user: CurrentUser):
    """Return the authenticated user's profile."""
    return current_user


@router.patch("/me", response_model=UserPublic)
async def update_me(data: UserUpdate, current_user: CurrentUser, db: DBSession):
    """Update the authenticated user's profile fields."""
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/{username}", response_model=UserPublic)
async def get_user(username: str, db: DBSession):
    """Fetch a public user profile by username."""
    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/{username}/follow", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def follow(request: Request, username: str, current_user: CurrentUser, db: DBSession):
    """
    Follow a user. For remote (federated) users, sends an AP Follow activity and
    marks the follow as pending until the remote server sends an Accept.
    """
    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot follow yourself")

    existing = await db.execute(
        select(Follow).where(Follow.follower_id == current_user.id, Follow.followed_id == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Already following this user")

    # Remote follows are pending until the remote server sends Accept
    is_pending = user.is_remote and settings.federation_enabled
    db.add(Follow(follower_id=current_user.id, followed_id=user.id, is_pending=is_pending))
    await db.commit()

    if is_pending and user.ap_inbox:
        activity = build_follow(current_user.username, actor_id(user.username) if not user.ap_id else user.ap_id)
        try:
            await deliver_activity(activity, current_user, [user.ap_inbox])
        except Exception:
            pass  # delivery failure never blocks the local follow row


@router.delete("/{username}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow(username: str, current_user: CurrentUser, db: DBSession):
    """
    Unfollow a user. For remote (federated) users, sends an AP Undo{Follow} activity.
    """
    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    result = await db.execute(
        select(Follow).where(Follow.follower_id == current_user.id, Follow.followed_id == user.id)
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
            pass
