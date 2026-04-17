import logging

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel
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
from app.schemas.device_token import DeviceTokenCreate
from app.schemas.post import PostPublic
from app.schemas.user import DeleteAccountRequest, UserPublic, UserUpdate

logger = logging.getLogger("pimpam.users")

router = APIRouter(prefix="/users", tags=["users"])


async def _resolve_user_urls(user_pub: UserPublic) -> UserPublic:
    """Resolve avatar_url and cover_image_url S3 keys to signed URLs."""
    from app.core.media_urls import resolve_urls

    keys = [user_pub.avatar_url, user_pub.cover_image_url]
    resolved = await resolve_urls(keys)
    return user_pub.model_copy(
        update={"avatar_url": resolved[0], "cover_image_url": resolved[1]}
    )


class _UserBrief(BaseModel):
    user_id: int
    username: str
    avatar_url: str | None = None


@router.get("/autocomplete", response_model=list[_UserBrief])
@limiter.limit("60/minute")
async def autocomplete_users(
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
    q: str = Query(..., min_length=1, max_length=50),
    limit: int = Query(default=5, le=10),
):
    """Lightweight username-prefix search for @mention autocomplete."""
    from app.models.user import User as UserModel

    result = await db.execute(
        select(UserModel.id, UserModel.username, UserModel.avatar_url)
        .where(
            UserModel.username.ilike(f"{q}%"),
            UserModel.is_active == True,  # noqa: E712
        )
        .order_by(UserModel.username)
        .limit(limit)
    )
    from app.core.media_urls import resolve_urls

    rows = result.all()
    avatar_keys = [row.avatar_url for row in rows]
    resolved = await resolve_urls(avatar_keys)
    return [
        _UserBrief(user_id=row.id, username=row.username, avatar_url=resolved[i])
        for i, row in enumerate(rows)
    ]


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: UnverifiedCurrentUser, db: DBSession):
    """Return the authenticated user's own profile, including verification, deletion status, and follower counts."""
    fc = await get_follower_count(db, current_user.id)
    fing = await get_following_count(db, current_user.id)
    pub = UserPublic.model_validate(current_user, from_attributes=True).model_copy(
        update={"follower_count": fc, "following_count": fing}
    )
    return await _resolve_user_urls(pub)


@router.patch("/me", response_model=UserPublic)
async def update_me(
    data: UserUpdate, current_user: UnverifiedCurrentUser, db: DBSession
):
    """Update the authenticated user's profile fields."""
    import json
    from datetime import datetime, timedelta, timezone

    from app.models.pending_deletion import PendingDeletion

    updates = data.model_dump(exclude_unset=True)

    # Schedule old images for deletion when avatar or cover changes
    for img_field in ("avatar_url", "cover_image_url"):
        if img_field in updates and updates[img_field] != getattr(
            current_user, img_field
        ):
            old_key = getattr(current_user, img_field)
            if old_key and not old_key.startswith("http"):
                from fastapi.concurrency import run_in_threadpool

                from app.core.storage import get_object_size

                size = await run_in_threadpool(get_object_size, old_key)
                now = datetime.now(timezone.utc)
                db.add(
                    PendingDeletion(
                        s3_key=old_key,
                        scheduled_at=now,
                        delete_after=now + timedelta(hours=1),
                        user_id=current_user.id,
                        bytes_to_reclaim=size,
                    )
                )

    for field, value in updates.items():
        if field == "profile_layout":
            # Store as JSON string in the database
            setattr(
                current_user, field, json.dumps(value) if value is not None else None
            )
        elif field == "e2ee_public_key":
            import base64
            import hashlib

            setattr(current_user, field, value)
            if value:
                raw = base64.b64decode(value)
                current_user.e2ee_key_fingerprint = hashlib.sha256(raw).hexdigest()
                current_user.e2ee_key_set_at = datetime.now(timezone.utc)
            else:
                current_user.e2ee_key_fingerprint = None
                current_user.e2ee_key_set_at = None
        else:
            setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    await index_user(current_user)
    # Invalidate cached user data used by post enrichment
    from app.core.cache import cache_delete

    await cache_delete(f"user:{current_user.id}")
    fc = await get_follower_count(db, current_user.id)
    fing = await get_following_count(db, current_user.id)
    pub = UserPublic.model_validate(current_user, from_attributes=True).model_copy(
        update={"follower_count": fc, "following_count": fing}
    )
    return await _resolve_user_urls(pub)


@router.post("/me/pin/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def pin_post(post_id: int, current_user: CurrentUser, db: DBSession):
    """Pin one of your own posts to your profile."""
    from app.models.post import Post

    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="You can only pin your own posts"
        )
    current_user.pinned_post_id = post_id
    await db.commit()


@router.delete("/me/pin", status_code=status.HTTP_204_NO_CONTENT)
async def unpin_post(current_user: CurrentUser, db: DBSession):
    """Remove the pinned post from your profile."""
    current_user.pinned_post_id = None
    await db.commit()


@router.get("/{username}/community-stats")
async def get_community_stats(
    username: str, db: DBSession, current_user: OptionalUser = None
):
    """Return community membership stats for a user."""
    from sqlalchemy import case, func

    from app.models.community import CommunityMember
    from app.schemas.user import CommunityStatsPublic

    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    # If the user hid their stats and this isn't their own profile, return 404
    is_own = current_user is not None and current_user.id == user.id
    if not user.show_community_stats and not is_own:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Community stats are hidden"
        )

    result = await db.execute(
        select(
            func.count().label("joined"),
            func.count(
                case(
                    (CommunityMember.role.in_(["moderator", "senior_mod"]), 1),
                )
            ).label("moderating"),
            func.count(
                case(
                    (CommunityMember.role == "owner", 1),
                )
            ).label("owned"),
        ).where(CommunityMember.user_id == user.id)
    )
    row = result.one()
    return CommunityStatsPublic(
        joined=row.joined, moderating=row.moderating, owned=row.owned
    )


@router.get("/me/suggestions", response_model=list[UserPublic])
@limiter.limit("10/minute")
async def get_follow_suggestions(
    request: Request, current_user: CurrentUser, db: DBSession
):
    """Return up to 20 suggested users based on friends-of-friends.

    Finds users followed by people you follow, ranked by how many of your
    followees also follow them (mutual_count). Excludes yourself and users
    you already follow.
    """
    from sqlalchemy import func as sa_func
    from sqlalchemy.orm import aliased

    from app.crud.block import get_blocked_user_ids, get_blocker_ids
    from app.models.user import User

    # Alias Follow for the two hops
    f1 = aliased(Follow)  # me -> my followees
    f2 = aliased(Follow)  # my followees -> their followees (suggestions)

    # Subquery: IDs I already follow (confirmed only)
    my_following_ids = select(Follow.followed_id).where(
        Follow.follower_id == current_user.id, Follow.is_pending.is_(False)
    )

    # Exclude blocked users from suggestions
    blocked_ids = await get_blocked_user_ids(db, current_user.id)
    blocker_ids = await get_blocker_ids(db, current_user.id)
    hidden_ids = blocked_ids | blocker_ids

    # Friends-of-friends query:
    # f1: me -> followee (confirmed)
    # f2: followee -> suggestion (confirmed)
    # Exclude myself, users I already follow, and blocked users
    stmt = (
        select(
            User,
            sa_func.count(f2.follower_id.distinct()).label("mutual_count"),
        )
        .join(f2, User.id == f2.followed_id)
        .join(f1, f2.follower_id == f1.followed_id)
        .where(
            f1.follower_id == current_user.id,
            f1.is_pending.is_(False),
            f2.is_pending.is_(False),
            User.id != current_user.id,
            User.id.not_in(my_following_ids),
        )
        .group_by(User.id)
        .order_by(sa_func.count(f2.follower_id.distinct()).desc())
        .limit(20)
    )

    if hidden_ids:
        stmt = stmt.where(User.id.not_in(hidden_ids))

    result = await db.execute(stmt)
    rows = result.all()

    suggestions = []
    for user, _mutual_count in rows:
        fc = await get_follower_count(db, user.id)
        fing = await get_following_count(db, user.id)
        pub = UserPublic.model_validate(user, from_attributes=True).model_copy(
            update={
                "follower_count": fc,
                "following_count": fing,
                "is_following": False,
            }
        )
        suggestions.append(await _resolve_user_urls(pub))

    return suggestions


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
    pub = UserPublic.model_validate(user, from_attributes=True).model_copy(
        update={
            "follower_count": fc,
            "following_count": fing,
            "is_following": is_following,
        }
    )
    return await _resolve_user_urls(pub)


@router.get("/{username}/followers", response_model=list[UserPublic])
async def list_followers(
    username: str,
    db: DBSession,
    current_user: OptionalUser = None,
    limit: int = Query(default=50, le=200),
):
    """Return the list of confirmed followers for a user, newest first.

    When authenticated, each user includes an ``is_following`` flag indicating
    whether the current user follows them.
    """
    from app.crud.user import check_is_following_batch

    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    followers = await get_followers(db, user.id, limit=limit)
    if current_user is None:
        results = [
            UserPublic.model_validate(f, from_attributes=True) for f in followers
        ]
        return [await _resolve_user_urls(r) for r in results]
    following_set = await check_is_following_batch(
        db, current_user.id, [f.id for f in followers]
    )
    results = [
        UserPublic.model_validate(f, from_attributes=True).model_copy(
            update={
                "is_following": None
                if f.id == current_user.id
                else f.id in following_set
            }
        )
        for f in followers
    ]
    return [await _resolve_user_urls(r) for r in results]


@router.get("/{username}/following", response_model=list[UserPublic])
async def list_following(
    username: str,
    db: DBSession,
    current_user: OptionalUser = None,
    limit: int = Query(default=50, le=200),
):
    """Return the list of users that this user is confirmed following, newest first.

    When authenticated, each user includes an ``is_following`` flag indicating
    whether the current user follows them.
    """
    from app.crud.user import check_is_following_batch

    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    following = await get_following(db, user.id, limit=limit)
    if current_user is None:
        results = [
            UserPublic.model_validate(f, from_attributes=True) for f in following
        ]
        return [await _resolve_user_urls(r) for r in results]
    following_set = await check_is_following_batch(
        db, current_user.id, [f.id for f in following]
    )
    results = [
        UserPublic.model_validate(f, from_attributes=True).model_copy(
            update={
                "is_following": None
                if f.id == current_user.id
                else f.id in following_set
            }
        )
        for f in following
    ]
    return [await _resolve_user_urls(r) for r in results]


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
    # If user has hidden posts on profile and requester is not the owner, return empty
    is_owner = current_user and current_user.id == user.id
    if not user.show_posts_on_profile and not is_owner:
        return []
    viewer_id = current_user.id if current_user else None
    posts = await get_user_posts(
        db, user.id, limit=limit, before_id=before_id, viewer_id=viewer_id
    )
    return await annotate_posts_with_user_vote(db, posts, viewer_id)


@router.post("/{username}/follow", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def follow(
    request: Request, username: str, current_user: CurrentUser, db: DBSession
):
    """
    Follow a user. For remote (federated) users, sends an AP Follow activity and
    marks the follow as pending until the remote server sends an Accept.
    """
    from app.crud.block import is_blocked_either_direction

    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cannot follow yourself"
        )

    if await is_blocked_either_direction(db, current_user.id, user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Cannot follow this user")

    existing = await db.execute(
        select(Follow).where(
            Follow.follower_id == current_user.id, Follow.followed_id == user.id
        )
    )
    if existing.scalar_one_or_none():
        return  # Already following — idempotent, just return 204

    # Remote follows are pending until the remote server sends Accept
    is_pending = user.is_remote and settings.federation_enabled
    db.add(
        Follow(follower_id=current_user.id, followed_id=user.id, is_pending=is_pending)
    )
    await db.commit()
    # Invalidate follower/following count caches
    from app.core.cache import cache_delete

    await cache_delete(f"following:{current_user.id}")
    await cache_delete(f"followers:{user.id}")

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
    follow_obj = result.scalar_one_or_none()
    if follow_obj is None:
        return  # Not following — idempotent, just return 204

    await db.delete(follow_obj)
    await db.commit()
    # Invalidate follower/following count caches
    from app.core.cache import cache_delete as _cache_del

    await _cache_del(f"following:{current_user.id}")
    await _cache_del(f"followers:{user.id}")

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


# ---------------------------------------------------------------------------
# User blocking
# ---------------------------------------------------------------------------


@router.get("/me/blocked")
async def list_blocked(current_user: CurrentUser, db: DBSession):
    """Return all users the authenticated user has blocked."""
    from app.core.media_urls import resolve_url
    from app.crud.block import get_blocked_users
    from app.models.user import User

    blocks = await get_blocked_users(db, current_user.id)
    result = []
    for b in blocks:
        blocked_user = await db.get(User, b.blocked_id)
        avatar = await resolve_url(blocked_user.avatar_url) if blocked_user else None
        result.append(
            {
                "id": b.id,
                "blocker_id": b.blocker_id,
                "blocked_id": b.blocked_id,
                "blocked_username": blocked_user.username if blocked_user else None,
                "blocked_avatar_url": avatar,
                "created_at": b.created_at.isoformat(),
            }
        )
    return result


@router.post("/{username}/block", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def block_user(
    request: Request, username: str, current_user: CurrentUser, db: DBSession
):
    """Block a user. Also removes any existing follow relationship in both directions."""
    from sqlalchemy import delete as sa_delete

    from app.crud.block import create_block, get_block

    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot block yourself")

    existing = await get_block(db, current_user.id, user.id)
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Already blocked")

    # Remove follows in both directions
    await db.execute(
        sa_delete(Follow).where(
            ((Follow.follower_id == current_user.id) & (Follow.followed_id == user.id))
            | (
                (Follow.follower_id == user.id)
                & (Follow.followed_id == current_user.id)
            )
        )
    )

    await create_block(db, current_user.id, user.id)


@router.delete("/{username}/block", status_code=status.HTTP_204_NO_CONTENT)
async def unblock_user(username: str, current_user: CurrentUser, db: DBSession):
    """Unblock a user."""
    from app.crud.block import remove_block

    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    removed = await remove_block(db, current_user.id, user.id)
    if not removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User is not blocked")


# ---------------------------------------------------------------------------
# Device tokens (APNs / FCM / Web Push)
# ---------------------------------------------------------------------------


@router.post(
    "/me/device-tokens",
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def register_token(
    request: Request,
    data: DeviceTokenCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Register a device push token. Updates platform if the token already exists."""
    from app.crud.device_token import register_device_token

    dt = await register_device_token(db, current_user.id, data.token, data.platform)
    return {
        "id": dt.id,
        "token": dt.token,
        "platform": dt.platform,
        "created_at": dt.created_at.isoformat(),
    }


@router.delete("/me/device-tokens/{token}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_token(token: str, current_user: CurrentUser, db: DBSession):
    """Remove a device push token (e.g. on logout)."""
    from app.crud.device_token import remove_device_token

    removed = await remove_device_token(db, current_user.id, token)
    if not removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Token not found")
