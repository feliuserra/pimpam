import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.core.dependencies import CurrentUser, DBSession
from app.core.limiter import limiter
from app.crud.post import get_post
from app.crud.report import create_report, get_report
from app.schemas.report import ReportCreate

logger = logging.getLogger("pimpam.reports")

router = APIRouter(tags=["reports"])


@router.post("/posts/{post_id}/report", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def report_post(
    request: Request,
    post_id: int,
    data: ReportCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Report a post for violating community guidelines."""
    post = await get_post(db, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")

    if post.author_id == current_user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cannot report your own post"
        )

    existing = await get_report(db, current_user.id, "post", post_id)
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="You have already reported this post"
        )

    report = await create_report(db, current_user.id, "post", post_id, data.reason)
    return {
        "id": report.id,
        "content_type": report.content_type,
        "content_id": report.content_id,
        "created_at": report.created_at.isoformat(),
    }


@router.post("/comments/{comment_id}/report", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def report_comment(
    request: Request,
    comment_id: int,
    data: ReportCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Report a comment for violating community guidelines."""
    from sqlalchemy import select

    from app.models.comment import Comment

    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if comment.author_id == current_user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cannot report your own comment"
        )

    existing = await get_report(db, current_user.id, "comment", comment_id)
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="You have already reported this comment"
        )

    report = await create_report(
        db, current_user.id, "comment", comment_id, data.reason
    )
    return {
        "id": report.id,
        "content_type": report.content_type,
        "content_id": report.content_id,
        "created_at": report.created_at.isoformat(),
    }
