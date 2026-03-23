from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DBSession
from app.core.limiter import limiter
from app.crud.user import get_user_by_username
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
    Follow a local user.

    TODO (federation): for remote users (is_remote=True), send an AP Follow activity
    to their inbox via delivery.py. Consider:
    - Fetching the remote actor's inbox URL from the RemoteActor cache.
    - Handling the Accept activity response asynchronously.
    - Storing the follow as "pending" until an Accept is received.
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

    db.add(Follow(follower_id=current_user.id, followed_id=user.id))
    await db.commit()


@router.delete("/{username}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow(username: str, current_user: CurrentUser, db: DBSession):
    """
    Unfollow a local user.

    TODO (federation): for remote users, send an AP Undo{Follow} activity to their inbox.
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
