"""
Site-wide admin endpoints.

All endpoints require is_admin=True (via CurrentAdmin dependency).
"""

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentAdmin, DBSession
from app.crud.admin import (
    admin_remove_comment,
    admin_remove_post,
    get_active_suspension,
    get_global_ban,
    get_report,
    global_ban_user,
    global_unban_user,
    list_content_removals,
    list_global_bans,
    list_reports,
    list_suspensions,
    resolve_report,
    suspend_user,
    unsuspend_user,
)
from app.crud.comment import get_comment
from app.crud.post import get_post
from app.crud.user import get_user_by_id
from app.schemas.admin import (
    ContentRemovalCreate,
    ContentRemovalPublic,
    GlobalBanCreate,
    GlobalBanPublic,
    ReportPublic,
    ReportResolve,
    SuspensionCreate,
    SuspensionPublic,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Reports ---


@router.get("/reports", response_model=list[ReportPublic])
async def get_reports(
    db: DBSession,
    admin: CurrentAdmin,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List all reports. Optionally filter by status (pending/resolved/dismissed)."""
    reports = await list_reports(
        db, status_filter=status_filter, limit=limit, offset=offset
    )
    # Enrich with reporter username
    result = []
    for r in reports:
        reporter = await get_user_by_id(db, r.reporter_id)
        result.append(
            ReportPublic(
                id=r.id,
                reporter_id=r.reporter_id,
                reporter_username=reporter.username if reporter else "deleted",
                content_type=r.content_type,
                content_id=r.content_id,
                reason=r.reason,
                status=r.status,
                resolved_by_id=r.resolved_by_id,
                resolved_at=r.resolved_at,
                created_at=r.created_at,
            )
        )
    return result


@router.post("/reports/{report_id}/resolve", status_code=status.HTTP_200_OK)
async def resolve_report_endpoint(
    report_id: int,
    body: ReportResolve,
    db: DBSession,
    admin: CurrentAdmin,
):
    """Resolve a report: dismiss it or remove the reported content."""
    report = await get_report(db, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found")
    if report.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Report already resolved")

    if body.action == "remove_content":
        # Remove the reported content
        reason = body.reason or report.reason
        if report.content_type == "post":
            post = await get_post(db, report.content_id)
            if post and not post.is_removed:
                await admin_remove_post(db, post, admin.id, reason)
        elif report.content_type == "comment":
            comment = await get_comment(db, report.content_id)
            if comment and not comment.is_removed:
                await admin_remove_comment(db, comment, admin.id, reason)
        resolved = await resolve_report(db, report, admin.id, "resolved")
    else:
        resolved = await resolve_report(db, report, admin.id, "dismissed")

    reporter = await get_user_by_id(db, resolved.reporter_id)
    return ReportPublic(
        id=resolved.id,
        reporter_id=resolved.reporter_id,
        reporter_username=reporter.username if reporter else "deleted",
        content_type=resolved.content_type,
        content_id=resolved.content_id,
        reason=resolved.reason,
        status=resolved.status,
        resolved_by_id=resolved.resolved_by_id,
        resolved_at=resolved.resolved_at,
        created_at=resolved.created_at,
    )


# --- Suspensions ---


@router.post("/users/{user_id}/suspend", response_model=SuspensionPublic)
async def suspend_user_endpoint(
    user_id: int,
    body: SuspensionCreate,
    db: DBSession,
    admin: CurrentAdmin,
):
    """Suspend a user (temporary, with optional expiry)."""
    target = await get_user_by_id(db, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == admin.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cannot suspend yourself"
        )
    if target.is_admin:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cannot suspend an admin"
        )

    existing = await get_active_suspension(db, user_id)
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="User is already suspended"
        )

    suspension = await suspend_user(
        db, user_id, admin.id, body.reason, expires_at=body.expires_at
    )
    return SuspensionPublic(
        id=suspension.id,
        user_id=suspension.user_id,
        username=target.username,
        suspended_by_id=suspension.suspended_by_id,
        reason=suspension.reason,
        expires_at=suspension.expires_at,
        is_active=suspension.is_active,
        created_at=suspension.created_at,
    )


@router.post("/users/{user_id}/unsuspend", status_code=status.HTTP_204_NO_CONTENT)
async def unsuspend_user_endpoint(
    user_id: int,
    db: DBSession,
    admin: CurrentAdmin,
):
    """Lift all active suspensions for a user."""
    target = await get_user_by_id(db, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    await unsuspend_user(db, user_id)


@router.get("/suspensions", response_model=list[SuspensionPublic])
async def list_suspensions_endpoint(
    db: DBSession,
    admin: CurrentAdmin,
    active_only: bool = Query(default=True),
    limit: int = Query(default=50, le=200),
):
    """List user suspensions."""
    suspensions = await list_suspensions(db, active_only=active_only, limit=limit)
    result = []
    for s in suspensions:
        user = await get_user_by_id(db, s.user_id)
        result.append(
            SuspensionPublic(
                id=s.id,
                user_id=s.user_id,
                username=user.username if user else "deleted",
                suspended_by_id=s.suspended_by_id,
                reason=s.reason,
                expires_at=s.expires_at,
                is_active=s.is_active,
                created_at=s.created_at,
            )
        )
    return result


# --- Global Bans ---


@router.post("/users/{user_id}/ban", response_model=GlobalBanPublic)
async def ban_user_endpoint(
    user_id: int,
    body: GlobalBanCreate,
    db: DBSession,
    admin: CurrentAdmin,
):
    """Permanently ban a user from the platform. Deactivates their account."""
    target = await get_user_by_id(db, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot ban yourself")
    if target.is_admin:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot ban an admin")

    existing = await get_global_ban(db, user_id)
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="User is already banned")

    ban = await global_ban_user(db, user_id, admin.id, body.reason)
    return GlobalBanPublic(
        id=ban.id,
        user_id=ban.user_id,
        username=target.username,
        banned_by_id=ban.banned_by_id,
        reason=ban.reason,
        created_at=ban.created_at,
    )


@router.post("/users/{user_id}/unban", status_code=status.HTTP_204_NO_CONTENT)
async def unban_user_endpoint(
    user_id: int,
    db: DBSession,
    admin: CurrentAdmin,
):
    """Remove a global ban and reactivate the user's account."""
    target = await get_user_by_id(db, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    existing = await get_global_ban(db, user_id)
    if not existing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User is not banned")
    await global_unban_user(db, user_id)


@router.get("/bans", response_model=list[GlobalBanPublic])
async def list_bans_endpoint(
    db: DBSession,
    admin: CurrentAdmin,
    limit: int = Query(default=50, le=200),
):
    """List all global bans."""
    bans = await list_global_bans(db, limit=limit)
    result = []
    for b in bans:
        user = await get_user_by_id(db, b.user_id)
        result.append(
            GlobalBanPublic(
                id=b.id,
                user_id=b.user_id,
                username=user.username if user else "deleted",
                banned_by_id=b.banned_by_id,
                reason=b.reason,
                created_at=b.created_at,
            )
        )
    return result


# --- Content Removal ---


@router.post(
    "/posts/{post_id}/remove",
    response_model=ContentRemovalPublic,
    status_code=status.HTTP_200_OK,
)
async def remove_post_endpoint(
    post_id: int,
    body: ContentRemovalCreate,
    db: DBSession,
    admin: CurrentAdmin,
):
    """Remove a post platform-wide (sets is_removed=True + creates audit log)."""
    post = await get_post(db, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.is_removed:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Post is already removed")
    removal = await admin_remove_post(db, post, admin.id, body.reason)
    return removal


@router.post(
    "/comments/{comment_id}/remove",
    response_model=ContentRemovalPublic,
    status_code=status.HTTP_200_OK,
)
async def remove_comment_endpoint(
    comment_id: int,
    body: ContentRemovalCreate,
    db: DBSession,
    admin: CurrentAdmin,
):
    """Remove a comment platform-wide."""
    comment = await get_comment(db, comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found")
    if comment.is_removed:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Comment is already removed"
        )
    removal = await admin_remove_comment(db, comment, admin.id, body.reason)
    return removal


@router.get("/content-removals", response_model=list[ContentRemovalPublic])
async def list_removals_endpoint(
    db: DBSession,
    admin: CurrentAdmin,
    limit: int = Query(default=50, le=200),
):
    """List content removal audit log."""
    return await list_content_removals(db, limit=limit)
