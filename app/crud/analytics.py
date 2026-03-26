"""Aggregate analytics queries. All privacy-respecting — counts only, no individual data."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import AdminContentRemoval, GlobalBan, UserSuspension
from app.models.comment import Comment
from app.models.community import Community
from app.models.message import Message
from app.models.post import Post
from app.models.report import Report
from app.models.story import Story
from app.models.user import User


async def get_overview(db: AsyncSession) -> dict:
    from app.core.cache import cache_get

    cached = await cache_get("analytics:overview")
    if cached is not None:
        return cached

    total_users = (
        await db.execute(
            select(func.count()).select_from(User).where(User.is_active.is_(True))
        )
    ).scalar() or 0

    total_posts = (
        await db.execute(select(func.count()).select_from(Post))
    ).scalar() or 0

    total_comments = (
        await db.execute(select(func.count()).select_from(Comment))
    ).scalar() or 0

    total_communities = (
        await db.execute(select(func.count()).select_from(Community))
    ).scalar() or 0

    # Active users: distinct authors of posts or comments in last 7 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    post_authors = select(Post.author_id).where(
        Post.created_at >= cutoff, Post.author_id.is_not(None)
    )
    comment_authors = select(Comment.author_id).where(
        Comment.created_at >= cutoff, Comment.author_id.is_not(None)
    )
    active_users = (
        await db.execute(
            select(
                func.count(
                    func.distinct(
                        post_authors.union(comment_authors).subquery().c.author_id
                    )
                )
            )
        )
    ).scalar() or 0

    result = {
        "total_users": total_users,
        "total_posts": total_posts,
        "total_comments": total_comments,
        "total_communities": total_communities,
        "active_users_7d": active_users,
    }
    from app.core.cache import cache_set

    await cache_set("analytics:overview", result, ttl=300)
    return result


_METRIC_MAP = {
    "signups": User,
    "posts": Post,
    "comments": Comment,
    "messages": Message,
    "stories": Story,
}


async def get_timeseries(db: AsyncSession, metric: str, days: int = 30) -> list[dict]:
    from app.core.cache import cache_get, cache_set

    model = _METRIC_MAP.get(metric)
    if model is None:
        return []

    cache_key = f"analytics:timeseries:{metric}:{days}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    date_col = func.date(model.created_at)

    result = await db.execute(
        select(date_col.label("day"), func.count().label("count"))
        .where(model.created_at >= cutoff)
        .group_by("day")
        .order_by("day")
    )

    data = [{"date": str(row.day), "count": row.count} for row in result.all()]
    await cache_set(cache_key, data, ttl=300)
    return data


async def get_top_communities(
    db: AsyncSession, days: int = 30, limit: int = 10
) -> list[dict]:
    from app.core.cache import cache_get, cache_set

    cache_key = f"analytics:top_communities:{days}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            Community.name,
            func.count(Post.id).label("post_count"),
            Community.member_count,
        )
        .join(Post, Post.community_id == Community.id)
        .where(Post.created_at >= cutoff)
        .group_by(Community.id, Community.name, Community.member_count)
        .order_by(func.count(Post.id).desc())
        .limit(limit)
    )

    data = [
        {
            "name": row.name,
            "post_count": row.post_count,
            "member_count": row.member_count,
        }
        for row in result.all()
    ]
    await cache_set(cache_key, data, ttl=300)
    return data


async def get_moderation_summary(db: AsyncSession, days: int = 30) -> dict:
    from app.core.cache import cache_get

    cache_key = f"analytics:moderation:{days}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    pending_reports = (
        await db.execute(
            select(func.count()).select_from(Report).where(Report.status == "pending")
        )
    ).scalar() or 0

    bans_count = (
        await db.execute(
            select(func.count())
            .select_from(GlobalBan)
            .where(GlobalBan.created_at >= cutoff)
        )
    ).scalar() or 0

    removals_count = (
        await db.execute(
            select(func.count())
            .select_from(AdminContentRemoval)
            .where(AdminContentRemoval.created_at >= cutoff)
        )
    ).scalar() or 0

    suspensions_count = (
        await db.execute(
            select(func.count())
            .select_from(UserSuspension)
            .where(UserSuspension.created_at >= cutoff)
        )
    ).scalar() or 0

    result = {
        "pending_reports": pending_reports,
        "bans_count": bans_count,
        "removals_count": removals_count,
        "suspensions_count": suspensions_count,
    }
    from app.core.cache import cache_set

    await cache_set(cache_key, result, ttl=300)
    return result
