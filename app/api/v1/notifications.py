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
from app.schemas.notification import NotificationPublic, PreferenceUpdate, UnreadCount

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationPublic])
async def list_notifications(
    current_user: CurrentUser,
    db: DBSession,
    limit: int = Query(default=20, le=100),
    before_id: int | None = Query(default=None),
):
    """
    Return your notification inbox — unread first, then read, newest first.
    Cursor-paginated via ``before_id``.
    The client should render ``group_count`` as ``>99`` when it exceeds 99.
    """
    return await get_notifications(db, current_user.id, limit=limit, before_id=before_id)


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
async def update_preference(data: PreferenceUpdate, current_user: CurrentUser, db: DBSession):
    """
    Enable or disable a notification type.
    Send ``{"notification_type": "vote", "enabled": false}`` to opt out of vote notifications.
    """
    await set_preference(db, current_user.id, data.notification_type, data.enabled)
