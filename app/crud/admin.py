from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import AdminContentRemoval, GlobalBan, UserSuspension
from app.models.comment import Comment
from app.models.post import Post
from app.models.report import Report
from app.models.user import User

# --- Reports ---


async def list_reports(
    db: AsyncSession,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Report]:
    """List reports, optionally filtered by status."""
    query = (
        select(Report).order_by(Report.created_at.desc()).limit(limit).offset(offset)
    )
    if status_filter:
        query = query.where(Report.status == status_filter)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_report(db: AsyncSession, report_id: int) -> Report | None:
    result = await db.execute(select(Report).where(Report.id == report_id))
    return result.scalar_one_or_none()


async def resolve_report(
    db: AsyncSession, report: Report, admin_id: int, status: str
) -> Report:
    """Mark a report as resolved (dismissed or actioned)."""
    report.status = status
    report.resolved_by_id = admin_id
    report.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(report)
    return report


# --- Suspensions ---


async def suspend_user(
    db: AsyncSession,
    user_id: int,
    admin_id: int,
    reason: str,
    expires_at: datetime | None = None,
) -> UserSuspension:
    suspension = UserSuspension(
        user_id=user_id,
        suspended_by_id=admin_id,
        reason=reason,
        expires_at=expires_at,
    )
    db.add(suspension)
    await db.commit()
    await db.refresh(suspension)
    return suspension


async def unsuspend_user(db: AsyncSession, user_id: int) -> None:
    """Deactivate all active suspensions for a user."""
    await db.execute(
        update(UserSuspension)
        .where(UserSuspension.user_id == user_id, UserSuspension.is_active == True)  # noqa: E712
        .values(is_active=False)
    )
    await db.commit()


async def get_active_suspension(
    db: AsyncSession, user_id: int
) -> UserSuspension | None:
    """Return the active suspension for a user, or None."""
    result = await db.execute(
        select(UserSuspension).where(
            UserSuspension.user_id == user_id,
            UserSuspension.is_active == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def list_suspensions(
    db: AsyncSession, active_only: bool = True, limit: int = 50
) -> list[UserSuspension]:
    query = (
        select(UserSuspension).order_by(UserSuspension.created_at.desc()).limit(limit)
    )
    if active_only:
        query = query.where(UserSuspension.is_active == True)  # noqa: E712
    result = await db.execute(query)
    return list(result.scalars().all())


# --- Global Bans ---


async def global_ban_user(
    db: AsyncSession, user_id: int, admin_id: int, reason: str
) -> GlobalBan:
    ban = GlobalBan(user_id=user_id, banned_by_id=admin_id, reason=reason)
    db.add(ban)
    # Also deactivate the user account
    await db.execute(update(User).where(User.id == user_id).values(is_active=False))
    await db.commit()
    await db.refresh(ban)
    return ban


async def global_unban_user(db: AsyncSession, user_id: int) -> None:
    """Remove global ban and reactivate user."""
    result = await db.execute(select(GlobalBan).where(GlobalBan.user_id == user_id))
    ban = result.scalar_one_or_none()
    if ban:
        await db.delete(ban)
        await db.execute(update(User).where(User.id == user_id).values(is_active=True))
        await db.commit()


async def get_global_ban(db: AsyncSession, user_id: int) -> GlobalBan | None:
    result = await db.execute(select(GlobalBan).where(GlobalBan.user_id == user_id))
    return result.scalar_one_or_none()


async def list_global_bans(db: AsyncSession, limit: int = 50) -> list[GlobalBan]:
    result = await db.execute(
        select(GlobalBan).order_by(GlobalBan.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


# --- Content Removal ---


async def admin_remove_post(
    db: AsyncSession, post: Post, admin_id: int, reason: str
) -> AdminContentRemoval:
    """Remove a post platform-wide and create audit log."""
    post.is_removed = True
    post.removed_by_id = admin_id
    removal = AdminContentRemoval(
        admin_id=admin_id, content_type="post", content_id=post.id, reason=reason
    )
    db.add(removal)
    await db.commit()
    await db.refresh(removal)
    return removal


async def admin_remove_comment(
    db: AsyncSession, comment: Comment, admin_id: int, reason: str
) -> AdminContentRemoval:
    """Remove a comment platform-wide and create audit log."""
    comment.is_removed = True
    comment.removed_by_id = admin_id
    removal = AdminContentRemoval(
        admin_id=admin_id, content_type="comment", content_id=comment.id, reason=reason
    )
    db.add(removal)
    await db.commit()
    await db.refresh(removal)
    return removal


async def list_content_removals(
    db: AsyncSession, limit: int = 50
) -> list[AdminContentRemoval]:
    result = await db.execute(
        select(AdminContentRemoval)
        .order_by(AdminContentRemoval.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
