from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DBSession
from app.crud.notification import (
    get_notifications,
    get_preferences,
    mark_all_read,
    mark_read,
    set_preference,
    unread_count,
)
from app.schemas.notification import (
    NotificationIds,
    NotificationPublic,
    PreferenceUpdate,
    UnreadCount,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


TYPE_GROUPS = {
    "follows": ["follow"],
    "karma": ["vote"],
    "comments": ["new_comment", "reply"],
}


@router.get("", response_model=list[NotificationPublic])
async def list_notifications(
    current_user: CurrentUser,
    db: DBSession,
    limit: int = Query(default=20, le=100),
    before_id: int | None = Query(default=None),
    type_group: str | None = Query(
        default=None, pattern="^(follows|karma|comments|other)$"
    ),
):
    """
    Return your notification inbox — unread first, then read, newest first.
    Cursor-paginated via ``before_id``.
    Filter by ``type_group``: follows, karma, comments, other.
    """
    from sqlalchemy import select as sa_select

    from app.models.user import User

    type_filter = None
    type_exclude = None
    if type_group == "other":
        type_exclude = ["follow", "vote", "new_comment", "reply"]
    elif type_group and type_group in TYPE_GROUPS:
        type_filter = TYPE_GROUPS[type_group]

    notifs = await get_notifications(
        db,
        current_user.id,
        limit=limit,
        before_id=before_id,
        type_filter=type_filter,
        type_exclude=type_exclude,
    )

    from app.core.media_urls import resolve_urls

    actor_ids = {n.actor_id for n in notifs if n.actor_id is not None}
    actors: dict[int, tuple[str, str | None]] = {}
    if actor_ids:
        rows = await db.execute(
            sa_select(User.id, User.username, User.avatar_url).where(
                User.id.in_(actor_ids)
            )
        )
        raw = list(rows)
        avatar_keys = [r.avatar_url for r in raw]
        resolved = await resolve_urls(avatar_keys)
        actors = {r.id: (r.username, resolved[i]) for i, r in enumerate(raw)}

    return [
        NotificationPublic.model_validate(n, from_attributes=True).model_copy(
            update={
                "actor_username": actors.get(n.actor_id, (None, None))[0]
                if n.actor_id
                else None,
                "actor_avatar_url": actors.get(n.actor_id, (None, None))[1]
                if n.actor_id
                else None,
            }
        )
        for n in notifs
    ]


@router.get("/unread-count", response_model=UnreadCount)
async def get_unread_count(current_user: CurrentUser, db: DBSession):
    """Return the number of unread notifications. Suitable for a badge counter."""
    count = await unread_count(db, current_user.id)
    return UnreadCount(count=count)


@router.patch("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def read_all(current_user: CurrentUser, db: DBSession):
    """Mark all unread notifications as read."""
    await mark_all_read(db, current_user.id)


@router.patch("/{notification_id}/read", response_model=NotificationPublic)
async def read_one(notification_id: int, current_user: CurrentUser, db: DBSession):
    """Mark a single notification as read."""
    notif = await mark_read(db, notification_id, current_user.id)
    if notif is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notif


@router.get("/preferences", response_model=list[str])
async def list_preferences(current_user: CurrentUser, db: DBSession):
    """
    Return the list of notification types you have disabled.
    All types are enabled by default — an empty list means everything is on.
    """
    return await get_preferences(db, current_user.id)


@router.patch("/preferences", status_code=status.HTTP_204_NO_CONTENT)
async def update_preference(
    data: PreferenceUpdate, current_user: CurrentUser, db: DBSession
):
    """
    Enable or disable a notification type.
    Send ``{"notification_type": "vote", "enabled": false}`` to opt out of vote notifications.
    """
    await set_preference(db, current_user.id, data.notification_type, data.enabled)


# --- Dismiss / Batch ---


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_one(notification_id: int, current_user: CurrentUser, db: DBSession):
    """Dismiss (delete) a single notification."""
    from app.crud.notification import delete_notification

    ok = await delete_notification(db, notification_id, current_user.id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Notification not found")


@router.post("/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_batch(
    body: NotificationIds, current_user: CurrentUser, db: DBSession
):
    """Dismiss (delete) multiple notifications at once."""
    from app.crud.notification import delete_notifications_batch

    await delete_notifications_batch(db, body.ids, current_user.id)


@router.post("/mark-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read_many(
    body: NotificationIds, current_user: CurrentUser, db: DBSession
):
    """Mark multiple notifications as read at once."""
    from app.crud.notification import mark_read_batch

    await mark_read_batch(db, body.ids, current_user.id)
