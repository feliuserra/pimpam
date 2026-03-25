from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.issue import Issue, IssueComment, IssueVote


async def create_issue(
    db: AsyncSession,
    author_id: int,
    title: str,
    description: str,
    category: str,
    device_info: str | None = None,
) -> Issue:
    issue = Issue(
        author_id=author_id,
        title=title,
        description=description,
        category=category,
        device_info=device_info,
    )
    db.add(issue)
    await db.commit()
    await db.refresh(issue)
    return issue


async def get_issue(db: AsyncSession, issue_id: int) -> Issue | None:
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    return result.scalar_one_or_none()


async def list_issues(
    db: AsyncSession,
    sort: str = "votes",
    category: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Issue]:
    query = select(Issue)
    if category:
        query = query.where(Issue.category == category)
    if status_filter:
        query = query.where(Issue.status == status_filter)
    if sort == "votes":
        query = query.order_by(Issue.vote_count.desc(), Issue.created_at.desc())
    else:
        query = query.order_by(Issue.created_at.desc())
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def vote_issue(db: AsyncSession, issue_id: int, user_id: int) -> bool:
    """Add a vote. Returns True if vote was added, False if already voted."""
    existing = await db.execute(
        select(IssueVote).where(
            IssueVote.issue_id == issue_id, IssueVote.user_id == user_id
        )
    )
    if existing.scalar_one_or_none():
        return False
    db.add(IssueVote(issue_id=issue_id, user_id=user_id))
    issue = await get_issue(db, issue_id)
    if issue:
        issue.vote_count += 1
    await db.commit()
    return True


async def unvote_issue(db: AsyncSession, issue_id: int, user_id: int) -> bool:
    """Remove a vote. Returns True if vote was removed, False if not voted."""
    result = await db.execute(
        select(IssueVote).where(
            IssueVote.issue_id == issue_id, IssueVote.user_id == user_id
        )
    )
    vote = result.scalar_one_or_none()
    if not vote:
        return False
    await db.delete(vote)
    issue = await get_issue(db, issue_id)
    if issue:
        issue.vote_count = max(0, issue.vote_count - 1)
    await db.commit()
    return True


async def has_voted(db: AsyncSession, issue_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(IssueVote).where(
            IssueVote.issue_id == issue_id, IssueVote.user_id == user_id
        )
    )
    return result.scalar_one_or_none() is not None


async def has_voted_batch(
    db: AsyncSession, issue_ids: list[int], user_id: int
) -> set[int]:
    """Return the subset of issue_ids that user_id has voted on."""
    if not issue_ids:
        return set()
    result = await db.execute(
        select(IssueVote.issue_id).where(
            IssueVote.user_id == user_id, IssueVote.issue_id.in_(issue_ids)
        )
    )
    return set(result.scalars().all())


async def create_issue_comment(
    db: AsyncSession, issue_id: int, author_id: int, content: str
) -> IssueComment:
    comment = IssueComment(issue_id=issue_id, author_id=author_id, content=content)
    db.add(comment)
    # Update comment count
    issue = await get_issue(db, issue_id)
    if issue:
        issue.comment_count += 1
    await db.commit()
    await db.refresh(comment)
    return comment


async def list_issue_comments(
    db: AsyncSession, issue_id: int, limit: int = 50, offset: int = 0
) -> list[IssueComment]:
    result = await db.execute(
        select(IssueComment)
        .where(IssueComment.issue_id == issue_id)
        .order_by(IssueComment.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
