from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.follow import Follow
from app.models.friend_group import FriendGroup, FriendGroupMember
from app.models.user import User
from app.schemas.friend_group import FriendGroupMemberPublic, FriendGroupPublic


async def get_or_create_close_friends(db: AsyncSession, owner_id: int) -> FriendGroup:
    """Return the Close Friends group for owner_id, creating it if it doesn't exist."""
    result = await db.execute(
        select(FriendGroup).where(
            FriendGroup.owner_id == owner_id,
            FriendGroup.is_close_friends == True,  # noqa: E712
        )
    )
    group = result.scalar_one_or_none()
    if group is None:
        group = FriendGroup(owner_id=owner_id, name="Close Friends", is_close_friends=True)
        db.add(group)
        await db.commit()
        await db.refresh(group)
    return group


async def get_group(db: AsyncSession, group_id: int) -> FriendGroup | None:
    result = await db.execute(select(FriendGroup).where(FriendGroup.id == group_id))
    return result.scalar_one_or_none()


async def get_owner_groups(db: AsyncSession, owner_id: int) -> list[FriendGroupPublic]:
    """Return all groups owned by the user, each with member_count (no member list)."""
    groups_result = await db.execute(
        select(FriendGroup).where(FriendGroup.owner_id == owner_id).order_by(
            FriendGroup.is_close_friends.desc(),  # Close Friends first
            FriendGroup.created_at,
        )
    )
    groups = list(groups_result.scalars().all())
    if not groups:
        return []

    group_ids = [g.id for g in groups]
    counts_result = await db.execute(
        select(FriendGroupMember.group_id, func.count().label("cnt"))
        .where(FriendGroupMember.group_id.in_(group_ids))
        .group_by(FriendGroupMember.group_id)
    )
    counts = {row.group_id: row.cnt for row in counts_result}

    return [
        FriendGroupPublic(
            id=g.id,
            name=g.name,
            is_close_friends=g.is_close_friends,
            member_count=counts.get(g.id, 0),
            members=[],
            created_at=g.created_at,
        )
        for g in groups
    ]


async def get_group_detail(db: AsyncSession, group: FriendGroup) -> FriendGroupPublic:
    """Return a group with its full member list (user_id + username)."""
    members_result = await db.execute(
        select(FriendGroupMember, User.username)
        .join(User, User.id == FriendGroupMember.member_id)
        .where(FriendGroupMember.group_id == group.id)
        .order_by(FriendGroupMember.added_at)
    )
    rows = members_result.all()
    members = [
        FriendGroupMemberPublic(user_id=m.member_id, username=username, added_at=m.added_at)
        for m, username in rows
    ]
    return FriendGroupPublic(
        id=group.id,
        name=group.name,
        is_close_friends=group.is_close_friends,
        member_count=len(members),
        members=members,
        created_at=group.created_at,
    )


async def create_group(db: AsyncSession, owner_id: int, name: str) -> FriendGroup:
    group = FriendGroup(owner_id=owner_id, name=name, is_close_friends=False)
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


async def rename_group(db: AsyncSession, group: FriendGroup, name: str) -> FriendGroup:
    group.name = name
    await db.commit()
    await db.refresh(group)
    return group


async def delete_group(db: AsyncSession, group: FriendGroup) -> None:
    await db.delete(group)
    await db.commit()


async def add_member(db: AsyncSession, group: FriendGroup, user_id: int) -> FriendGroupMember:
    """
    Add user_id to the group.
    Raises ValueError('not_following') if the group owner doesn't follow user_id.
    Raises ValueError('already_member') if already in group.
    Sends a notification to the added user.
    """
    # Verify owner follows this user
    follow = await db.execute(
        select(Follow).where(
            Follow.follower_id == group.owner_id,
            Follow.followed_id == user_id,
            Follow.is_pending == False,  # noqa: E712
        )
    )
    if follow.scalar_one_or_none() is None:
        raise ValueError("not_following")

    # Check not already a member
    existing = await db.execute(
        select(FriendGroupMember).where(
            FriendGroupMember.group_id == group.id,
            FriendGroupMember.member_id == user_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError("already_member")

    member = FriendGroupMember(group_id=group.id, member_id=user_id)
    db.add(member)
    await db.commit()
    await db.refresh(member)

    # Notify the added user
    try:
        from app.crud.notification import notify
        await notify(db, user_id, "friend_group_added", actor_id=group.owner_id)
    except Exception:
        pass

    return member


async def remove_member(db: AsyncSession, group: FriendGroup, user_id: int) -> None:
    """
    Remove user_id from the group.
    Raises ValueError('not_member') if user_id is not in the group.
    Sends a notification to the removed user.
    """
    result = await db.execute(
        select(FriendGroupMember).where(
            FriendGroupMember.group_id == group.id,
            FriendGroupMember.member_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise ValueError("not_member")

    await db.delete(member)
    await db.commit()

    try:
        from app.crud.notification import notify
        await notify(db, user_id, "friend_group_removed", actor_id=group.owner_id)
    except Exception:
        pass


async def is_member(db: AsyncSession, group_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(FriendGroupMember).where(
            FriendGroupMember.group_id == group_id,
            FriendGroupMember.member_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None
