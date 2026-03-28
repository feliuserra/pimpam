"""Aggregate analytics queries. All privacy-respecting — counts only, no individual data."""

from collections import defaultdict
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


async def _dialect_is_postgres(db: AsyncSession) -> bool:
    """Return True when the session is backed by PostgreSQL.

    Checks the live connection's dialect name so the result is accurate
    even when tests override the session with an in-memory SQLite engine.
    """
    try:
        conn = await db.connection()
        return conn.sync_connection.dialect.name == "postgresql"
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Time-window configuration
# ---------------------------------------------------------------------------

_WINDOW_CONFIG = {
    "1h": {"delta": timedelta(hours=1), "trunc": "minute", "points": 12},
    "24h": {"delta": timedelta(hours=24), "trunc": "hour", "points": 24},
    "7d": {"delta": timedelta(days=7), "trunc": "day", "points": 7},
    "30d": {"delta": timedelta(days=30), "trunc": "day", "points": 30},
}

_METRIC_MAP = {
    "signups": User,
    "posts": Post,
    "comments": Comment,
    "messages": Message,
    "stories": Story,
}


# ---------------------------------------------------------------------------
# Existing functions (unchanged)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# New: window-relative network health overview
# ---------------------------------------------------------------------------


async def get_window_overview(db: AsyncSession, window: str) -> dict:
    """Return active/new users, new posts, new messages within the given window."""
    from app.core.cache import cache_get, cache_set

    cfg = _WINDOW_CONFIG.get(window, _WINDOW_CONFIG["24h"])
    cutoff = datetime.now(timezone.utc) - cfg["delta"]

    # Short TTL for the 1-hour window so security-relevant data is fresh
    cache_key = f"analytics:window_overview:{window}"
    ttl = 30 if window == "1h" else 300
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    new_users = (
        await db.execute(
            select(func.count()).select_from(User).where(User.created_at >= cutoff)
        )
    ).scalar() or 0

    new_posts = (
        await db.execute(
            select(func.count()).select_from(Post).where(Post.created_at >= cutoff)
        )
    ).scalar() or 0

    new_messages = (
        await db.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.created_at >= cutoff)
        )
    ).scalar() or 0

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
        "active_users": active_users,
        "new_users": new_users,
        "new_posts": new_posts,
        "new_messages": new_messages,
        "window_label": window,
    }
    await cache_set(cache_key, result, ttl=ttl)
    return result


# ---------------------------------------------------------------------------
# New: granular timeseries with auto-bucketing
# ---------------------------------------------------------------------------


def _bucket_timestamps_in_python(timestamps: list[datetime], trunc: str) -> list[dict]:
    """Bucket a list of datetimes in Python — used as a SQLite fallback in tests."""
    counts: dict[str, int] = defaultdict(int)
    for ts in timestamps:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if trunc == "minute":
            # 5-minute buckets
            bucket_minute = (ts.minute // 5) * 5
            key = ts.replace(minute=bucket_minute, second=0, microsecond=0).isoformat()
        elif trunc == "hour":
            key = ts.replace(minute=0, second=0, microsecond=0).isoformat()
        else:
            key = ts.date().isoformat()
        counts[key] += 1
    return [{"bucket": k, "count": v} for k, v in sorted(counts.items())]


async def get_granular_timeseries(
    db: AsyncSession, metric: str, window: str
) -> list[dict]:
    """
    Return time-bucketed counts with auto-granularity:
      1h  → 5-minute buckets
      24h → 1-hour buckets
      7d / 30d → 1-day buckets

    Uses PostgreSQL date_trunc for efficiency; falls back to Python bucketing
    on SQLite (used in the test suite).
    """
    from app.core.cache import cache_get, cache_set

    model = _METRIC_MAP.get(metric)
    if model is None:
        return []

    cfg = _WINDOW_CONFIG.get(window, _WINDOW_CONFIG["24h"])
    cutoff = datetime.now(timezone.utc) - cfg["delta"]
    trunc = cfg["trunc"]

    cache_key = f"analytics:granular:{metric}:{window}"
    ttl = 30 if window == "1h" else 300
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    if await _dialect_is_postgres(db):
        # PostgreSQL path: server-side bucketing via date_trunc / epoch arithmetic
        if trunc == "minute":
            epoch = func.extract("epoch", model.created_at).cast("bigint")
            bucket_expr = func.to_timestamp((epoch / 300) * 300)
        else:
            bucket_expr = func.date_trunc(trunc, model.created_at)

        result = await db.execute(
            select(bucket_expr.label("bucket"), func.count().label("count"))
            .where(model.created_at >= cutoff)
            .group_by("bucket")
            .order_by("bucket")
        )
        data = [
            {"bucket": row.bucket.isoformat(), "count": row.count}
            for row in result.all()
        ]
    else:
        # SQLite fallback (test suite uses in-memory SQLite which lacks date_trunc)
        result = await db.execute(
            select(model.created_at).where(model.created_at >= cutoff)
        )
        timestamps = list(result.scalars().all())
        data = _bucket_timestamps_in_python(timestamps, trunc)

    await cache_set(cache_key, data, ttl=ttl)
    return data


# ---------------------------------------------------------------------------
# New: security metrics
# ---------------------------------------------------------------------------


async def get_security_metrics(db: AsyncSession, window: str) -> dict:
    """
    Return login attempt counts, failure rate, password reset requests,
    new registrations, and suspicious IP hashes for the given window.

    Always uses a 30-second cache TTL so security data refreshes quickly.
    """
    from app.core.cache import cache_get, cache_set
    from app.crud.login_attempt import count_attempts_in_window, get_suspicious_ips
    from app.models.password_reset import PasswordResetToken

    cfg = _WINDOW_CONFIG.get(window, _WINDOW_CONFIG["1h"])
    cutoff = datetime.now(timezone.utc) - cfg["delta"]

    cache_key = f"analytics:security:{window}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    failed = await count_attempts_in_window(db, cutoff, success=False)
    successful = await count_attempts_in_window(db, cutoff, success=True)
    total = failed + successful
    failure_rate = round(failed / total, 4) if total > 0 else 0.0

    resets = (
        await db.execute(
            select(func.count())
            .select_from(PasswordResetToken)
            .where(PasswordResetToken.created_at >= cutoff)
        )
    ).scalar() or 0

    new_registrations = (
        await db.execute(
            select(func.count()).select_from(User).where(User.created_at >= cutoff)
        )
    ).scalar() or 0

    suspicious_ips = await get_suspicious_ips(db, cutoff, min_failures=10)

    result = {
        "window_label": window,
        "failed_logins": failed,
        "successful_logins": successful,
        "failure_rate": failure_rate,
        "password_reset_requests": resets,
        "new_registrations": new_registrations,
        "suspicious_ips": suspicious_ips,
    }
    await cache_set(cache_key, result, ttl=30)
    return result


# ---------------------------------------------------------------------------
# New: security alert detection
# ---------------------------------------------------------------------------


async def get_security_alerts(db: AsyncSession) -> dict:
    """
    Evaluate threshold rules against the last hour and return a list of alerts.

    This function is intentionally never cached — it must always reflect the
    latest state so that admins see alerts as soon as thresholds are breached.

    Rules:
      1. high_failure_rate   — > 50 failed logins in the last hour
      2. login_failure_ratio — failure rate > 30% with >= 10 total attempts
      3. registration_spike  — hourly registrations > 5× 30-day rolling average
    """
    from app.crud.login_attempt import count_attempts_in_window

    now = datetime.now(timezone.utc)
    cutoff_1h = now - timedelta(hours=1)
    alerts = []

    failed_1h = await count_attempts_in_window(db, cutoff_1h, success=False)

    # Rule 1: absolute brute-force threshold
    if failed_1h > 50:
        alerts.append(
            {
                "alert_type": "high_failure_rate",
                "message": f"{failed_1h} failed login attempts in the last hour.",
                "value": float(failed_1h),
                "threshold": 50.0,
            }
        )

    # Rule 2: failure ratio (only meaningful with enough traffic)
    successful_1h = await count_attempts_in_window(db, cutoff_1h, success=True)
    total_1h = failed_1h + successful_1h
    if total_1h >= 10:
        failure_rate = failed_1h / total_1h
        if failure_rate > 0.30:
            alerts.append(
                {
                    "alert_type": "login_failure_ratio",
                    "message": f"Login failure rate is {failure_rate:.0%} in the last hour.",
                    "value": round(failure_rate, 4),
                    "threshold": 0.30,
                }
            )

    # Rule 3: registration spike vs. 30-day rolling average
    cutoff_30d = now - timedelta(days=30)
    regs_baseline = (
        await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.created_at >= cutoff_30d, User.created_at < cutoff_1h)
        )
    ).scalar() or 0

    # Hourly average from 30-day baseline (excluding the current hour)
    hourly_avg = regs_baseline / (30 * 24 - 1)

    regs_1h = (
        await db.execute(
            select(func.count()).select_from(User).where(User.created_at >= cutoff_1h)
        )
    ).scalar() or 0

    spike_threshold = hourly_avg * 5
    if hourly_avg > 0 and regs_1h > spike_threshold:
        alerts.append(
            {
                "alert_type": "registration_spike",
                "message": (
                    f"{regs_1h} new registrations in the last hour "
                    f"(baseline avg {hourly_avg:.1f}/h)."
                ),
                "value": float(regs_1h),
                "threshold": round(spike_threshold, 2),
            }
        )

    return {
        "alerts": alerts,
        "generated_at": now,
    }
