import re

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hashtag import Hashtag, PostHashtag

# Match #word patterns — letters, numbers, underscores; at least 1 char after #
HASHTAG_RE = re.compile(r"#([a-zA-Z0-9_]\w{0,99})", re.UNICODE)


def extract_hashtags(text: str) -> list[str]:
    """Extract unique, lowercase hashtag names from text."""
    if not text:
        return []
    tags = HASHTAG_RE.findall(text)
    seen: set[str] = set()
    result: list[str] = []
    for tag in tags:
        lower = tag.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(lower)
    return result


async def get_or_create_hashtags(db: AsyncSession, names: list[str]) -> list[Hashtag]:
    """Get existing hashtags or create new ones. Returns Hashtag objects."""
    if not names:
        return []

    # Fetch existing
    result = await db.execute(select(Hashtag).where(Hashtag.name.in_(names)))
    existing = {h.name: h for h in result.scalars().all()}

    hashtags: list[Hashtag] = []
    for name in names:
        if name in existing:
            hashtags.append(existing[name])
        else:
            h = Hashtag(name=name)
            db.add(h)
            hashtags.append(h)

    if any(h.id is None for h in hashtags):
        await db.flush()

    return hashtags


async def sync_post_hashtags(
    db: AsyncSession, post_id: int, content: str, title: str = ""
) -> list[str]:
    """
    Extract hashtags from post content+title, sync the post_hashtags table,
    and update hashtag post_counts. Returns the list of hashtag names.
    """
    names = extract_hashtags(f"{title} {content}" if title else content)

    # Get current hashtags for this post
    current = await db.execute(
        select(PostHashtag.hashtag_id).where(PostHashtag.post_id == post_id)
    )
    current_ids = set(current.scalars().all())

    if not names and not current_ids:
        return []

    # Get or create hashtag objects
    hashtags = await get_or_create_hashtags(db, names)
    new_ids = {h.id for h in hashtags}

    # Remove old associations
    to_remove = current_ids - new_ids
    if to_remove:
        await db.execute(
            delete(PostHashtag).where(
                PostHashtag.post_id == post_id,
                PostHashtag.hashtag_id.in_(to_remove),
            )
        )

    # Add new associations
    to_add = new_ids - current_ids
    for hashtag_id in to_add:
        db.add(PostHashtag(post_id=post_id, hashtag_id=hashtag_id))

    if to_remove or to_add:
        await db.flush()
        # Recount affected hashtags
        affected_ids = to_remove | to_add
        for hid in affected_ids:
            count_result = await db.execute(
                select(func.count(PostHashtag.id)).where(PostHashtag.hashtag_id == hid)
            )
            count = count_result.scalar_one()
            await db.execute(
                Hashtag.__table__.update()
                .where(Hashtag.id == hid)
                .values(post_count=count)
            )

    return names


async def get_trending_hashtags(db: AsyncSession, limit: int = 20) -> list[Hashtag]:
    """Return hashtags ordered by post_count descending."""
    result = await db.execute(
        select(Hashtag)
        .where(Hashtag.post_count > 0)
        .order_by(Hashtag.post_count.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_hashtag_by_name(db: AsyncSession, name: str) -> Hashtag | None:
    """Find a hashtag by its normalized name."""
    result = await db.execute(select(Hashtag).where(Hashtag.name == name.lower()))
    return result.scalar_one_or_none()


async def search_hashtags(
    db: AsyncSession, query: str, limit: int = 20
) -> list[Hashtag]:
    """Search hashtags by prefix match."""
    q = query.lower().lstrip("#")
    if not q:
        return []
    result = await db.execute(
        select(Hashtag)
        .where(Hashtag.name.startswith(q))
        .order_by(Hashtag.post_count.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_post_ids_for_hashtag(
    db: AsyncSession,
    hashtag_id: int,
    limit: int = 50,
    before_id: int | None = None,
) -> list[int]:
    """Return post IDs tagged with a given hashtag, newest first."""
    query = select(PostHashtag.post_id).where(PostHashtag.hashtag_id == hashtag_id)
    if before_id is not None:
        query = query.where(PostHashtag.post_id < before_id)
    query = query.order_by(PostHashtag.post_id.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
