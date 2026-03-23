from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.federation.crypto import generate_rsa_keypair
from app.models.follow import Follow
from app.models.user import User
from app.schemas.user import UserCreate


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_ap_id(db: AsyncSession, ap_id: str) -> User | None:
    result = await db.execute(select(User).where(User.ap_id == ap_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    private_pem, public_pem = generate_rsa_keypair()
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        display_name=data.display_name or data.username,
        ap_public_key_pem=public_pem,
        ap_private_key_pem=private_pem,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    user = await get_user_by_username(db, username)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


async def get_local_follower_ids(db: AsyncSession, user_id: int) -> list[int]:
    """Return IDs of all confirmed local (non-remote) followers of user_id."""
    result = await db.execute(
        select(Follow.follower_id)
        .join(User, User.id == Follow.follower_id)
        .where(
            Follow.followed_id == user_id,
            User.is_remote == False,  # noqa: E712
            Follow.is_pending == False,  # noqa: E712
        )
    )
    return list(result.scalars().all())


async def get_remote_follower_inboxes(db: AsyncSession, user_id: int) -> list[str]:
    """Return inbox URLs of all confirmed remote followers of user_id (for AP delivery)."""
    result = await db.execute(
        select(User.ap_inbox)
        .join(Follow, Follow.follower_id == User.id)
        .where(
            Follow.followed_id == user_id,
            User.is_remote == True,  # noqa: E712
            User.ap_inbox.is_not(None),
            Follow.is_pending == False,  # noqa: E712
        )
    )
    return [row for row in result.scalars().all() if row]
