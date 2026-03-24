"""
Friend groups and Close Friends list.

GET    /api/v1/friend-groups                        — list your groups
POST   /api/v1/friend-groups                        — create a named group
GET    /api/v1/friend-groups/close-friends           — get (or create) the Close Friends group
GET    /api/v1/friend-groups/{id}                   — group detail with full member list
PATCH  /api/v1/friend-groups/{id}                   — rename a group
DELETE /api/v1/friend-groups/{id}                   — delete a group
POST   /api/v1/friend-groups/{id}/members           — add a member {user_id}
DELETE /api/v1/friend-groups/{id}/members/{user_id} — remove a member
"""
from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DBSession
from app.crud.friend_group import (
    add_member,
    create_group,
    delete_group,
    get_group,
    get_group_detail,
    get_or_create_close_friends,
    get_owner_groups,
    remove_member,
    rename_group,
)
from app.schemas.friend_group import (
    FriendGroupCreate,
    FriendGroupMemberAdd,
    FriendGroupPublic,
    FriendGroupRename,
)

router = APIRouter(prefix="/friend-groups", tags=["friend-groups"])


@router.get("", response_model=list[FriendGroupPublic])
async def list_groups(current_user: CurrentUser, db: DBSession):
    """List all friend groups you own, with member counts. Close Friends appears first."""
    return await get_owner_groups(db, current_user.id)


@router.post("", response_model=FriendGroupPublic, status_code=status.HTTP_201_CREATED)
async def create(data: FriendGroupCreate, current_user: CurrentUser, db: DBSession):
    """Create a new named friend group."""
    group = await create_group(db, current_user.id, data.name)
    return await get_group_detail(db, group)


@router.get("/close-friends", response_model=FriendGroupPublic)
async def get_close_friends(current_user: CurrentUser, db: DBSession):
    """
    Return the Close Friends group, creating it automatically if it doesn't exist yet.
    This is the group used when you post with visibility ``"group"`` and select Close Friends.
    """
    group = await get_or_create_close_friends(db, current_user.id)
    return await get_group_detail(db, group)


@router.get("/{group_id}", response_model=FriendGroupPublic)
async def get_detail(group_id: int, current_user: CurrentUser, db: DBSession):
    """Return group detail including the full member list."""
    group = await get_group(db, group_id)
    if group is None or group.owner_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Group not found")
    return await get_group_detail(db, group)


@router.patch("/{group_id}", response_model=FriendGroupPublic)
async def rename(group_id: int, data: FriendGroupRename, current_user: CurrentUser, db: DBSession):
    """Rename a friend group. The Close Friends group cannot be renamed."""
    group = await get_group(db, group_id)
    if group is None or group.owner_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Group not found")
    if group.is_close_friends:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot rename the Close Friends group")
    group = await rename_group(db, group, data.name)
    return await get_group_detail(db, group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(group_id: int, current_user: CurrentUser, db: DBSession):
    """Delete a friend group. The Close Friends group cannot be deleted."""
    group = await get_group(db, group_id)
    if group is None or group.owner_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Group not found")
    if group.is_close_friends:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot delete the Close Friends group")
    await delete_group(db, group)


@router.post("/{group_id}/members", response_model=FriendGroupPublic, status_code=status.HTTP_201_CREATED)
async def add(group_id: int, data: FriendGroupMemberAdd, current_user: CurrentUser, db: DBSession):
    """
    Add a user to the group. You must be following them.
    The added user receives a notification.
    """
    group = await get_group(db, group_id)
    if group is None or group.owner_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Group not found")
    if data.user_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot add yourself to a group")
    try:
        await add_member(db, group, data.user_id)
    except ValueError as e:
        err = str(e)
        if err == "not_following":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="You must follow this user to add them")
        if err == "already_member":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Already a member of this group")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=err)
    return await get_group_detail(db, group)


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(group_id: int, user_id: int, current_user: CurrentUser, db: DBSession):
    """Remove a member from the group. The removed user receives a notification."""
    group = await get_group(db, group_id)
    if group is None or group.owner_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Group not found")
    try:
        await remove_member(db, group, user_id)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User is not a member of this group")
