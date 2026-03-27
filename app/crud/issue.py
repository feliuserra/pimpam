from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.issue import (
    Issue,
    IssueComment,
    IssuePoll,
    IssuePollOption,
    IssuePollVote,
    IssueVote,
)
from app.schemas.issue import PollCreate


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
    closed: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Issue]:
    query = select(Issue)
    if category:
        query = query.where(Issue.category == category)
    if status_filter:
        query = query.where(Issue.status == status_filter)
    if closed is not None:
        query = query.where(Issue.is_closed == closed)
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


async def close_issue(db: AsyncSession, issue: Issue) -> Issue:
    """Mark an issue as closed."""
    from datetime import datetime, timezone

    issue.is_closed = True
    issue.closed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(issue)
    return issue


async def reopen_issue(db: AsyncSession, issue: Issue) -> Issue:
    """Reopen a closed issue."""
    issue.is_closed = False
    issue.closed_at = None
    await db.commit()
    await db.refresh(issue)
    return issue


# --- Poll CRUD ---


async def create_poll(
    db: AsyncSession, issue_id: int, poll_data: PollCreate
) -> IssuePoll:
    """Create a poll attached to an issue with its options."""
    poll = IssuePoll(
        issue_id=issue_id,
        question=poll_data.question,
        allows_multiple=poll_data.allows_multiple,
    )
    db.add(poll)
    await db.flush()  # get poll.id for options

    for i, opt in enumerate(poll_data.options):
        db.add(
            IssuePollOption(
                poll_id=poll.id,
                text=opt.text.strip(),
                display_order=i,
            )
        )
    await db.commit()
    await db.refresh(poll)
    return poll


async def get_poll_for_issue(
    db: AsyncSession, issue_id: int, user_id: int | None = None
) -> dict | None:
    """Return poll data for an issue, including options and user's votes."""
    result = await db.execute(select(IssuePoll).where(IssuePoll.issue_id == issue_id))
    poll = result.scalar_one_or_none()
    if not poll:
        return None

    # Fetch options ordered by display_order
    opts_result = await db.execute(
        select(IssuePollOption)
        .where(IssuePollOption.poll_id == poll.id)
        .order_by(IssuePollOption.display_order)
    )
    options = list(opts_result.scalars().all())

    # Total votes across all options
    total_result = await db.execute(
        select(func.count(IssuePollVote.id)).where(
            IssuePollVote.option_id.in_([o.id for o in options])
        )
    )
    total_votes = total_result.scalar() or 0

    # User's voted option IDs
    user_voted_option_ids: list[int] = []
    if user_id:
        voted_result = await db.execute(
            select(IssuePollVote.option_id).where(
                IssuePollVote.user_id == user_id,
                IssuePollVote.option_id.in_([o.id for o in options]),
            )
        )
        user_voted_option_ids = list(voted_result.scalars().all())

    return {
        "id": poll.id,
        "question": poll.question,
        "allows_multiple": poll.allows_multiple,
        "options": [
            {
                "id": o.id,
                "text": o.text,
                "vote_count": o.vote_count,
                "display_order": o.display_order,
            }
            for o in options
        ],
        "total_votes": total_votes,
        "user_voted_option_ids": user_voted_option_ids,
    }


async def vote_poll(db: AsyncSession, user_id: int, option_id: int) -> bool:
    """Cast a vote on a poll option. Returns True if vote was added."""
    # Get the option and its poll
    opt_result = await db.execute(
        select(IssuePollOption).where(IssuePollOption.id == option_id)
    )
    option = opt_result.scalar_one_or_none()
    if not option:
        return False

    poll_result = await db.execute(
        select(IssuePoll).where(IssuePoll.id == option.poll_id)
    )
    poll = poll_result.scalar_one_or_none()
    if not poll:
        return False

    # Check if user already voted on this option
    existing = await db.execute(
        select(IssuePollVote).where(
            IssuePollVote.option_id == option_id,
            IssuePollVote.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none():
        return False

    # If single-choice, remove any existing votes on other options in this poll
    if not poll.allows_multiple:
        all_opts = await db.execute(
            select(IssuePollOption.id).where(IssuePollOption.poll_id == poll.id)
        )
        all_opt_ids = list(all_opts.scalars().all())
        prev_votes = await db.execute(
            select(IssuePollVote).where(
                IssuePollVote.user_id == user_id,
                IssuePollVote.option_id.in_(all_opt_ids),
            )
        )
        for prev in prev_votes.scalars().all():
            # Decrement old option's count
            old_opt = await db.execute(
                select(IssuePollOption).where(IssuePollOption.id == prev.option_id)
            )
            old_option = old_opt.scalar_one_or_none()
            if old_option:
                old_option.vote_count = max(0, old_option.vote_count - 1)
            await db.delete(prev)

    # Add the new vote
    db.add(IssuePollVote(option_id=option_id, user_id=user_id))
    option.vote_count += 1
    await db.commit()
    return True


async def unvote_poll(db: AsyncSession, user_id: int, option_id: int) -> bool:
    """Remove a vote from a poll option. Returns True if vote was removed."""
    result = await db.execute(
        select(IssuePollVote).where(
            IssuePollVote.option_id == option_id,
            IssuePollVote.user_id == user_id,
        )
    )
    vote = result.scalar_one_or_none()
    if not vote:
        return False

    await db.delete(vote)

    # Decrement option vote count
    opt_result = await db.execute(
        select(IssuePollOption).where(IssuePollOption.id == option_id)
    )
    option = opt_result.scalar_one_or_none()
    if option:
        option.vote_count = max(0, option.vote_count - 1)

    await db.commit()
    return True
