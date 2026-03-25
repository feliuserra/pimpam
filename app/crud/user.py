import hashlib
import random  # noqa: F401 — used in create_user for avatar assignment
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.federation.crypto import generate_rsa_keypair
from app.models.comment import Comment
from app.models.community import Community
from app.models.community_karma import CommunityKarma
from app.models.consent import ConsentLog
from app.models.follow import Follow
from app.models.message import Message
from app.models.post import Post
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


_CAT_AVATARS = [f"/avatars/cat-{i:02d}.svg" for i in range(1, 21)]


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    private_pem, public_pem = generate_rsa_keypair()
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        display_name=data.display_name or data.username,
        avatar_url=random.choice(_CAT_AVATARS),
        ap_public_key_pem=public_pem,
        ap_private_key_pem=private_pem,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> User | None:
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


async def get_follower_count(db: AsyncSession, user_id: int) -> int:
    """Return the number of confirmed (non-pending) followers."""
    result = await db.execute(
        select(func.count(Follow.id)).where(
            Follow.followed_id == user_id,
            Follow.is_pending == False,  # noqa: E712
        )
    )
    return result.scalar_one()


async def get_following_count(db: AsyncSession, user_id: int) -> int:
    """Return the number of users this user is confirmed following."""
    result = await db.execute(
        select(func.count(Follow.id)).where(
            Follow.follower_id == user_id,
            Follow.is_pending == False,  # noqa: E712
        )
    )
    return result.scalar_one()


async def check_is_following(
    db: AsyncSession, follower_id: int, followed_id: int
) -> bool:
    """Return True if follower_id follows followed_id (confirmed, non-pending)."""
    result = await db.execute(
        select(Follow).where(
            Follow.follower_id == follower_id,
            Follow.followed_id == followed_id,
            Follow.is_pending == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none() is not None


async def get_followers(db: AsyncSession, user_id: int, limit: int = 50) -> list[User]:
    """Return confirmed followers of user_id, newest first."""
    result = await db.execute(
        select(User)
        .join(Follow, Follow.follower_id == User.id)
        .where(
            Follow.followed_id == user_id,
            Follow.is_pending == False,  # noqa: E712
        )
        .order_by(Follow.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_following(db: AsyncSession, user_id: int, limit: int = 50) -> list[User]:
    """Return users that user_id is confirmed following, newest first."""
    result = await db.execute(
        select(User)
        .join(Follow, Follow.followed_id == User.id)
        .where(
            Follow.follower_id == user_id,
            Follow.is_pending == False,  # noqa: E712
        )
        .order_by(Follow.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def record_consent(
    db: AsyncSession,
    user_id: int,
    consent_type: str,
    version: str,
    ip: str | None = None,
) -> None:
    """Record a consent event for GDPR audit trail. IP is stored as SHA-256 hash only."""
    ip_hash = hashlib.sha256(ip.encode()).hexdigest() if ip else None
    db.add(
        ConsentLog(
            user_id=user_id, consent_type=consent_type, version=version, ip_hash=ip_hash
        )
    )


async def get_user_data_export(db: AsyncSession, user_id: int) -> dict:
    """Assemble a full GDPR data export for user_id. All queries are explicit selects — no lazy loads."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()

    posts = (
        (
            await db.execute(
                select(Post)
                .where(Post.author_id == user_id, Post.is_removed == False)  # noqa: E712
                .order_by(Post.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    comments = (
        (
            await db.execute(
                select(Comment)
                .where(Comment.author_id == user_id, Comment.is_removed == False)  # noqa: E712
                .order_by(Comment.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    messages_sent = (
        (
            await db.execute(
                select(Message)
                .where(Message.sender_id == user_id)
                .order_by(Message.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    messages_received = (
        (
            await db.execute(
                select(Message)
                .where(Message.recipient_id == user_id)
                .order_by(Message.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    following_rows = (
        (
            await db.execute(
                select(User.username)
                .join(Follow, Follow.followed_id == User.id)
                .where(Follow.follower_id == user_id, Follow.is_pending == False)  # noqa: E712
            )
        )
        .scalars()
        .all()
    )

    follower_rows = (
        (
            await db.execute(
                select(User.username)
                .join(Follow, Follow.follower_id == User.id)
                .where(Follow.followed_id == user_id, Follow.is_pending == False)  # noqa: E712
            )
        )
        .scalars()
        .all()
    )

    karma_rows = (
        await db.execute(
            select(CommunityKarma, Community.name)
            .join(Community, Community.id == CommunityKarma.community_id)
            .where(CommunityKarma.user_id == user_id)
        )
    ).all()

    consent_rows = (
        (
            await db.execute(
                select(ConsentLog)
                .where(ConsentLog.user_id == user_id)
                .order_by(ConsentLog.created_at)
            )
        )
        .scalars()
        .all()
    )

    def _ts(dt: datetime | None) -> str | None:
        return dt.isoformat() if dt else None

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "bio": user.bio,
            "avatar_url": user.avatar_url,
            "karma": user.karma,
            "is_verified": user.is_verified,
            "created_at": _ts(user.created_at),
        },
        "posts": [
            {
                "id": p.id,
                "title": p.title,
                "content": p.content,
                "visibility": p.visibility,
                "community_id": p.community_id,
                "created_at": _ts(p.created_at),
            }
            for p in posts
        ],
        "comments": [
            {
                "id": c.id,
                "post_id": c.post_id,
                "content": c.content,
                "created_at": _ts(c.created_at),
            }
            for c in comments
        ],
        "messages_sent": [
            {
                "id": m.id,
                "recipient_id": m.recipient_id,
                "ciphertext": m.ciphertext,
                "created_at": _ts(m.created_at),
            }
            for m in messages_sent
        ],
        "messages_received": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "ciphertext": m.ciphertext,
                "created_at": _ts(m.created_at),
            }
            for m in messages_received
        ],
        "following": list(following_rows),
        "followers": list(follower_rows),
        "community_karma": [
            {"community": name, "karma": ck.karma} for ck, name in karma_rows
        ],
        "consent_log": [
            {
                "consent_type": cl.consent_type,
                "version": cl.version,
                "created_at": _ts(cl.created_at),
            }
            for cl in consent_rows
        ],
    }


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
