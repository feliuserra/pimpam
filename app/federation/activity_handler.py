"""
Process verified incoming ActivityPub activities.

The inbox router calls the appropriate handler after signature verification.
Unknown activity types return silently — the AP spec requires servers not to
error on unknown activities.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user import get_user_by_ap_id
from app.federation.actor import build_accept
from app.federation.delivery import deliver_activity
from app.models.follow import Follow
from app.models.post import Post


async def dispatch(activity: dict, db: AsyncSession) -> None:
    """Route an incoming activity to the correct handler."""
    handlers = {
        "Follow": _handle_follow,
        "Undo": _handle_undo,
        "Create": _handle_create,
        "Delete": _handle_delete,
        "Accept": _handle_accept,
    }
    handler = handlers.get(activity.get("type"))
    if handler:
        await handler(activity, db)


# --- Individual handlers ---


async def _handle_follow(activity: dict, db: AsyncSession) -> None:
    """Remote actor follows a local user. Auto-accept immediately."""
    actor_ap_id: str = activity.get("actor", "")
    object_ap_id: str = activity.get("object", "")

    local_user = await get_user_by_ap_id(db, object_ap_id)
    if local_user is None:
        return  # addressed to an unknown local user — ignore

    remote_user = await _get_or_create_remote_user(actor_ap_id, db)
    if remote_user is None:
        return

    # Upsert the Follow row (idempotent)
    existing = await db.execute(
        select(Follow).where(
            Follow.follower_id == remote_user.id,
            Follow.followed_id == local_user.id,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(Follow(follower_id=remote_user.id, followed_id=local_user.id))
        await db.commit()

    # Send Accept back to the remote actor's inbox
    accept = build_accept(local_user.username, activity)
    from app.federation.fetcher import fetch_remote_actor

    actor_doc = await fetch_remote_actor(actor_ap_id, db)
    inbox_url = actor_doc.get("inbox", "")
    if inbox_url:
        await deliver_activity(accept, local_user, [inbox_url])


async def _handle_undo(activity: dict, db: AsyncSession) -> None:
    """Handle Undo{Follow} — remote actor unfollows a local user."""
    obj = activity.get("object", {})
    if isinstance(obj, dict) and obj.get("type") == "Follow":
        actor_ap_id: str = activity.get("actor", "")
        followed_ap_id: str = obj.get("object", "")
        remote_user = await get_user_by_ap_id(db, actor_ap_id)
        local_user = await get_user_by_ap_id(db, followed_ap_id)
        if remote_user and local_user:
            result = await db.execute(
                select(Follow).where(
                    Follow.follower_id == remote_user.id,
                    Follow.followed_id == local_user.id,
                )
            )
            follow = result.scalar_one_or_none()
            if follow:
                await db.delete(follow)
                await db.commit()


async def _handle_create(activity: dict, db: AsyncSession) -> None:
    """Cache a federated Note as a local Post."""
    obj = activity.get("object", {})
    if not isinstance(obj, dict) or obj.get("type") != "Note":
        return

    ap_id: str = obj.get("id", "")
    if not ap_id:
        return

    # Idempotent: skip if we already have this post
    existing = await db.execute(select(Post).where(Post.ap_id == ap_id))
    if existing.scalar_one_or_none():
        return

    actor_ap_id: str = activity.get("actor", "")
    remote_author = await _get_or_create_remote_user(actor_ap_id, db)
    if remote_author is None:
        return

    content: str = obj.get("content", "")
    title = (
        content[:100].rstrip() if content else "(untitled)"
    )  # Note has no title field

    post = Post(
        title=title,
        content=content,
        author_id=remote_author.id,
        ap_id=ap_id,
    )
    db.add(post)
    await db.commit()


async def _handle_delete(activity: dict, db: AsyncSession) -> None:
    """Delete a locally cached remote post."""
    obj = activity.get("object")
    ap_id = obj if isinstance(obj, str) else (obj or {}).get("id")
    if not ap_id:
        return

    result = await db.execute(select(Post).where(Post.ap_id == ap_id))
    post = result.scalar_one_or_none()
    if post:
        await db.delete(post)
        await db.commit()


async def _handle_accept(activity: dict, db: AsyncSession) -> None:
    """
    Remote server accepted our outgoing Follow request.
    Clear the is_pending flag so the follow becomes active in feeds.
    """
    obj = activity.get("object", {})
    # Accept.object may be the full Follow activity dict or just its ID string.
    # Many servers (Mastodon, Pleroma) send just the IRI string.
    if isinstance(obj, str):
        # The actor is the remote server that accepted our Follow.
        # Find any pending follow from a local user to this remote actor.
        followed_ap_id = activity.get("actor", "")
        followed = await get_user_by_ap_id(db, followed_ap_id)
        if followed is None:
            return
        result = await db.execute(
            select(Follow).where(
                Follow.followed_id == followed.id,
                Follow.is_pending == True,  # noqa: E712
            )
        )
        follow = result.scalar_one_or_none()
        if follow:
            follow.is_pending = False
            await db.commit()
        return

    if not isinstance(obj, dict) or obj.get("type") != "Follow":
        return

    follower_ap_id: str = obj.get("actor", "")
    followed_ap_id: str = obj.get("object", "")

    follower = await get_user_by_ap_id(db, follower_ap_id)
    followed = await get_user_by_ap_id(db, followed_ap_id)
    if follower is None or followed is None:
        return

    result = await db.execute(
        select(Follow).where(
            Follow.follower_id == follower.id,
            Follow.followed_id == followed.id,
            Follow.is_pending == True,  # noqa: E712
        )
    )
    follow = result.scalar_one_or_none()
    if follow:
        follow.is_pending = False
        await db.commit()


# --- Helpers ---


async def _get_or_create_remote_user(ap_id: str, db: AsyncSession):
    """
    Find or create a stub User row for a remote actor.
    Remote users have is_remote=True and ap_id set; no password or keys.
    """
    from app.federation.fetcher import FederationFetchError, fetch_remote_actor
    from app.models.user import User

    user = await get_user_by_ap_id(db, ap_id)
    if user:
        return user

    try:
        actor_doc = await fetch_remote_actor(ap_id, db)
    except FederationFetchError:
        return None

    username = actor_doc.get("preferredUsername", "")
    domain = ap_id.split("/")[2]
    # Qualify the username with the domain to avoid collisions with local users
    unique_username = f"{username}@{domain}"

    user = User(
        username=unique_username,
        email=f"{unique_username}@remote.invalid",  # placeholder, never used for login
        hashed_password="",  # remote users cannot log in locally
        display_name=actor_doc.get("name") or username,
        ap_id=ap_id,
        ap_inbox=actor_doc.get("inbox"),
        is_remote=True,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
