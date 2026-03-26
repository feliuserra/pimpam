import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationPreference

logger = logging.getLogger("pimpam.notifications")


async def is_opted_out(db: AsyncSession, user_id: int, notification_type: str) -> bool:
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.notification_type == notification_type,
        )
    )
    return result.scalar_one_or_none() is not None


async def notify(
    db: AsyncSession,
    user_id: int,
    notification_type: str,
    *,
    actor_id: int | None = None,
    post_id: int | None = None,
    comment_id: int | None = None,
    community_id: int | None = None,
    story_id: int | None = None,
    group_key: str | None = None,
) -> None:
    """
    Create or update a notification, then push a real-time WS event.
    Entirely fire-and-forget — all exceptions are swallowed.
    Skipped silently if the user has opted out of this type.
    Do not notify a user about their own actions (actor == recipient).
    """
    try:
        if actor_id is not None and actor_id == user_id:
            return
        if await is_opted_out(db, user_id, notification_type):
            return

        notif: Notification | None = None

        if group_key is not None:
            # Find an existing unread grouped notification to update
            result = await db.execute(
                select(Notification).where(
                    Notification.user_id == user_id,
                    Notification.group_key == group_key,
                    Notification.is_read == False,  # noqa: E712
                )
            )
            notif = result.scalar_one_or_none()

        if notif is not None:
            notif.group_count += 1
            notif.created_at = datetime.now(timezone.utc)
            if actor_id is not None:
                notif.actor_id = actor_id  # update to most recent actor
        else:
            notif = Notification(
                user_id=user_id,
                type=notification_type,
                actor_id=actor_id,
                post_id=post_id,
                comment_id=comment_id,
                community_id=community_id,
                story_id=story_id,
                group_key=group_key,
                group_count=1,
            )
            db.add(notif)

        await db.commit()
        if notif.id is None:
            await db.refresh(notif)

        # Push real-time event — fire-and-forget
        from app.core.redis import publish_to_user

        await publish_to_user(
            user_id,
            "notification",
            {
                "id": notif.id,
                "type": notification_type,
                "group_count": notif.group_count,
                "actor_id": actor_id,
                "post_id": post_id,
                "comment_id": comment_id,
                "community_id": community_id,
                "story_id": story_id,
            },
        )
    except Exception:
        logger.exception(
            "Failed to create notification (type=%s, user=%s)",
            notification_type,
            user_id,
        )


async def get_notifications(
    db: AsyncSession,
    user_id: int,
    limit: int = 20,
    before_id: int | None = None,
    type_filter: list[str] | None = None,
    type_exclude: list[str] | None = None,
) -> list[Notification]:
    """
    Return notifications for a user — unread first, then read, newest first within each group.
    Cursor-paginated by id. Optionally filtered by notification type(s).
    """
    query = select(Notification).where(Notification.user_id == user_id)

    if before_id is not None:
        query = query.where(Notification.id < before_id)

    if type_filter:
        query = query.where(Notification.type.in_(type_filter))

    if type_exclude:
        query = query.where(Notification.type.notin_(type_exclude))

    query = query.order_by(
        Notification.is_read.asc(),
        Notification.created_at.desc(),
    ).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


async def mark_read(
    db: AsyncSession, notification_id: int, user_id: int
) -> Notification | None:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notif = result.scalar_one_or_none()
    if notif is None:
        return None
    notif.is_read = True
    await db.commit()
    await db.refresh(notif)
    return notif


async def mark_all_read(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    await db.commit()
    return result.rowcount


async def unread_count(db: AsyncSession, user_id: int) -> int:
    from sqlalchemy import func

    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        )
    )
    return result.scalar_one()


async def delete_notification(
    db: AsyncSession, notification_id: int, user_id: int
) -> bool:
    """Delete a single notification. Returns True if deleted."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notif = result.scalar_one_or_none()
    if notif is None:
        return False
    await db.delete(notif)
    await db.commit()
    return True


async def delete_notifications_batch(
    db: AsyncSession, notification_ids: list[int], user_id: int
) -> int:
    """Delete multiple notifications. Returns count deleted."""
    from sqlalchemy import delete as sa_delete

    result = await db.execute(
        sa_delete(Notification).where(
            Notification.id.in_(notification_ids),
            Notification.user_id == user_id,
        )
    )
    await db.commit()
    return result.rowcount


async def mark_read_batch(
    db: AsyncSession, notification_ids: list[int], user_id: int
) -> int:
    """Mark multiple notifications as read. Returns count updated."""
    result = await db.execute(
        update(Notification)
        .where(
            Notification.id.in_(notification_ids),
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        )
        .values(is_read=True)
    )
    await db.commit()
    return result.rowcount


async def get_preferences(db: AsyncSession, user_id: int) -> list[str]:
    """Return the list of notification types the user has disabled."""
    result = await db.execute(
        select(NotificationPreference.notification_type).where(
            NotificationPreference.user_id == user_id
        )
    )
    return list(result.scalars().all())


async def set_preference(
    db: AsyncSession, user_id: int, notification_type: str, enabled: bool
) -> None:
    """Enable or disable a notification type for a user."""
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.notification_type == notification_type,
        )
    )
    existing = result.scalar_one_or_none()

    if enabled and existing is not None:
        # Remove the disabled row → re-enables the type
        await db.delete(existing)
        await db.commit()
    elif not enabled and existing is None:
        # Add a disabled row
        db.add(
            NotificationPreference(user_id=user_id, notification_type=notification_type)
        )
        await db.commit()
