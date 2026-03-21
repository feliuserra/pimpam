from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DBSession
from app.crud.community import (
    create_community,
    get_community_by_name,
    join_community,
    leave_community,
)
from app.schemas.community import CommunityCreate, CommunityPublic

router = APIRouter(prefix="/communities", tags=["communities"])


@router.post("", response_model=CommunityPublic, status_code=status.HTTP_201_CREATED)
async def create(data: CommunityCreate, current_user: CurrentUser, db: DBSession):
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
