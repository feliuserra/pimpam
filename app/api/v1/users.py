from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DBSession
from app.crud.user import get_user_by_username
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
