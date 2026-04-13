"""
Community issue tracker — bugs, features, improvements.

Users submit and vote on issues. Most-voted items rise to the top.
Admins can update status and mark security items (non-negotiable).
"""

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.dependencies import CurrentAdmin, CurrentUser, DBSession, OptionalUser
from app.core.limiter import limiter
from app.crud.issue import (
    create_issue,
    create_issue_comment,
    create_poll,
    get_issue,
    get_poll_for_issue,
    has_voted,
    has_voted_batch,
    list_issue_comments,
    list_issues,
    unvote_issue,
    unvote_poll,
    vote_issue,
    vote_poll,
)
from app.crud.user import get_user_by_id
from app.schemas.issue import (
    IssueCommentCreate,
    IssueCommentPublic,
    IssueCreate,
    IssuePublic,
    IssueUpdate,
    PollPublic,
    PollVoteRequest,
)

router = APIRouter(prefix="/issues", tags=["issues"])


async def _enrich_issue(db, issue, user_id: int | None = None) -> IssuePublic:
    """Convert an Issue model to IssuePublic with author username, vote status, and poll."""
    author = await get_user_by_id(db, issue.author_id)
    voted = False
    if user_id:
        voted = await has_voted(db, issue.id, user_id)
    poll_data = await get_poll_for_issue(db, issue.id, user_id)
    poll = PollPublic(**poll_data) if poll_data else None
    return IssuePublic(
        id=issue.id,
        author_id=issue.author_id,
        author_username=author.username if author else "deleted",
        title=issue.title,
        description=issue.description,
        category=issue.category,
        status=issue.status,
        vote_count=issue.vote_count,
        comment_count=issue.comment_count,
        device_info=issue.device_info,
        is_security=issue.is_security,
        is_closed=issue.is_closed,
        closed_at=issue.closed_at,
        has_voted=voted,
        poll=poll,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
    )


@router.post("", response_model=IssuePublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def create(
    request: Request,
    body: IssueCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Submit a new issue or feature request, optionally with a poll."""
    issue = await create_issue(
        db,
        current_user.id,
        body.title,
        body.description,
        body.category,
        device_info=body.device_info,
    )
    if body.poll:
        await create_poll(db, issue.id, body.poll)
    return await _enrich_issue(db, issue, current_user.id)


@router.get("", response_model=list[IssuePublic])
async def list_all(
    db: DBSession,
    current_user: OptionalUser = None,
    sort: str = Query(default="votes", pattern="^(votes|recent)$"),
    category: str | None = Query(
        None, pattern="^(bug|feature|improvement|suggestion|complaint)$"
    ),
    status_filter: str | None = Query(
        None, alias="status", pattern="^(open|in_progress|completed|rejected)$"
    ),
    closed: bool | None = Query(None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List issues. Public endpoint — no auth required."""
    issues = await list_issues(
        db,
        sort=sort,
        category=category,
        status_filter=status_filter,
        closed=closed,
        limit=limit,
        offset=offset,
    )
    user_id = current_user.id if current_user else None
    # Batch check votes for efficiency
    if user_id and issues:
        voted_set = await has_voted_batch(db, [i.id for i in issues], user_id)
    else:
        voted_set = set()

    # Batch-fetch authors to avoid N+1
    author_ids = list({i.author_id for i in issues if i.author_id})
    authors_map: dict[int, str] = {}
    if author_ids:
        from sqlalchemy import select as _select

        from app.models.user import User as _User

        _a_result = await db.execute(
            _select(_User.id, _User.username).where(_User.id.in_(author_ids))
        )
        authors_map = {r.id: r.username for r in _a_result.all()}

    result = []
    for issue in issues:
        poll_data = await get_poll_for_issue(db, issue.id, user_id)
        poll = PollPublic(**poll_data) if poll_data else None
        result.append(
            IssuePublic(
                id=issue.id,
                author_id=issue.author_id,
                author_username=authors_map.get(issue.author_id, "deleted"),
                title=issue.title,
                description=issue.description,
                category=issue.category,
                status=issue.status,
                vote_count=issue.vote_count,
                comment_count=issue.comment_count,
                device_info=issue.device_info,
                is_security=issue.is_security,
                is_closed=issue.is_closed,
                closed_at=issue.closed_at,
                has_voted=issue.id in voted_set,
                poll=poll,
                created_at=issue.created_at,
                updated_at=issue.updated_at,
            )
        )
    return result


@router.get("/{issue_id}", response_model=IssuePublic)
async def get_one(
    issue_id: int,
    db: DBSession,
    current_user: OptionalUser = None,
):
    """Get a single issue by ID."""
    issue = await get_issue(db, issue_id)
    if issue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Issue not found")
    user_id = current_user.id if current_user else None
    return await _enrich_issue(db, issue, user_id)


# --- Voting ---


@router.post("/{issue_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
async def vote(
    issue_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """Upvote an issue. Idempotent — voting again is a no-op."""
    issue = await get_issue(db, issue_id)
    if issue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Issue not found")
    await vote_issue(db, issue_id, current_user.id)


@router.delete("/{issue_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
async def unvote(
    issue_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """Remove vote from an issue. Idempotent."""
    issue = await get_issue(db, issue_id)
    if issue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Issue not found")
    await unvote_issue(db, issue_id, current_user.id)


# --- Poll voting ---


@router.post("/{issue_id}/poll/vote", status_code=status.HTTP_204_NO_CONTENT)
async def vote_on_poll(
    issue_id: int,
    body: PollVoteRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """Vote on a poll option attached to an issue."""
    issue = await get_issue(db, issue_id)
    if issue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Issue not found")
    added = await vote_poll(db, current_user.id, body.option_id)
    if not added:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Already voted on this option"
        )


@router.delete("/{issue_id}/poll/vote", status_code=status.HTTP_204_NO_CONTENT)
async def unvote_on_poll(
    issue_id: int,
    body: PollVoteRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """Remove a poll vote."""
    issue = await get_issue(db, issue_id)
    if issue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Issue not found")
    await unvote_poll(db, current_user.id, body.option_id)


# --- Comments ---


@router.post(
    "/{issue_id}/comments",
    response_model=IssueCommentPublic,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/hour")
async def add_comment(
    request: Request,
    issue_id: int,
    body: IssueCommentCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Add a comment to an issue."""
    issue = await get_issue(db, issue_id)
    if issue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Issue not found")
    comment = await create_issue_comment(db, issue_id, current_user.id, body.content)
    return IssueCommentPublic(
        id=comment.id,
        issue_id=comment.issue_id,
        author_id=comment.author_id,
        author_username=current_user.username,
        is_admin=getattr(current_user, "is_admin", False),
        content=comment.content,
        created_at=comment.created_at,
    )


@router.get("/{issue_id}/comments", response_model=list[IssueCommentPublic])
async def get_comments(
    issue_id: int,
    db: DBSession,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List comments on an issue."""
    issue = await get_issue(db, issue_id)
    if issue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Issue not found")
    comments = await list_issue_comments(db, issue_id, limit=limit, offset=offset)

    # Batch-fetch authors to avoid N+1
    author_ids = list({c.author_id for c in comments if c.author_id})
    authors_map: dict[int, str] = {}
    admins_set: set[int] = set()
    if author_ids:
        from sqlalchemy import select as _select

        from app.models.user import User as _User

        _rows = await db.execute(
            _select(_User.id, _User.username, _User.is_admin).where(
                _User.id.in_(author_ids)
            )
        )
        for r in _rows.all():
            authors_map[r.id] = r.username
            if r.is_admin:
                admins_set.add(r.id)

    result = []
    for c in comments:
        result.append(
            IssueCommentPublic(
                id=c.id,
                issue_id=c.issue_id,
                author_id=c.author_id,
                author_username=authors_map.get(c.author_id, "deleted"),
                is_admin=c.author_id in admins_set,
                content=c.content,
                created_at=c.created_at,
            )
        )
    return result


# --- Admin ---


@router.patch("/{issue_id}", response_model=IssuePublic)
async def update_issue(
    issue_id: int,
    body: IssueUpdate,
    db: DBSession,
    admin: CurrentAdmin,
):
    """Admin-only: update issue status or security flag."""
    issue = await get_issue(db, issue_id)
    if issue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Issue not found")
    if body.status is not None:
        issue.status = body.status
    if body.is_security is not None:
        issue.is_security = body.is_security
    await db.commit()
    await db.refresh(issue)
    return await _enrich_issue(db, issue, admin.id)


# --- Close / Reopen ---


@router.post("/{issue_id}/close", response_model=IssuePublic)
async def close(
    issue_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """Close an issue. Author or admin only."""
    from app.crud.issue import close_issue

    issue = await get_issue(db, issue_id)
    if issue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Issue not found")
    is_admin = getattr(current_user, "is_admin", False)
    if issue.author_id != current_user.id and not is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not allowed")
    if issue.is_closed:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Issue is already closed")
    issue = await close_issue(db, issue)
    return await _enrich_issue(db, issue, current_user.id)


@router.post("/{issue_id}/reopen", response_model=IssuePublic)
async def reopen(
    issue_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """Reopen a closed issue. Author or admin only."""
    from app.crud.issue import reopen_issue

    issue = await get_issue(db, issue_id)
    if issue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Issue not found")
    is_admin = getattr(current_user, "is_admin", False)
    if issue.author_id != current_user.id and not is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not allowed")
    if not issue.is_closed:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Issue is not closed")
    issue = await reopen_issue(db, issue)
    return await _enrich_issue(db, issue, current_user.id)
