"""CRUD operations for stories — creation, feed queries, mentions."""

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.story import Story
from app.models.story_mention import StoryMention
from app.models.user import User
from app.schemas.story import LinkPreviewPublic, MentionedUser

_MENTION_RE = re.compile(r"@([a-zA-Z0-9_]{1,50})")

ALLOWED_DURATIONS = {12, 24, 48, 168}


async def create_story(
    db: AsyncSession,
    *,
    author_id: int,
    media_type: str,
    image_url: str | None = None,
    caption: str | None = None,
    duration_hours: int = 24,
    link_url: str | None = None,
    link_title: str | None = None,
    link_description: str | None = None,
    link_image_url: str | None = None,
) -> Story:
    """Create a story and return it (refreshed from DB)."""
    duration = duration_hours if duration_hours in ALLOWED_DURATIONS else 24
    story = Story(
        author_id=author_id,
        media_type=media_type,
        image_url=image_url,
        caption=caption,
        link_url=link_url,
        link_title=link_title,
        link_description=link_description,
        link_image_url=link_image_url,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=duration),
    )
    db.add(story)
    await db.commit()
    await db.refresh(story)
    return story


def extract_mentions(text: str) -> list[str]:
    """Extract unique @usernames from text. Returns lowercase list."""
    if not text:
        return []
    return list(dict.fromkeys(m.lower() for m in _MENTION_RE.findall(text)))


async def resolve_mentions(
    db: AsyncSession,
    usernames: list[str],
    max_count: int,
) -> list[User]:
    """Look up mentioned users by username. Returns up to max_count existing users."""
    if not usernames:
        return []
    usernames = usernames[:max_count]
    result = await db.execute(
        select(User).where(
            User.username.in_(usernames),
            User.is_active == True,  # noqa: E712
        )
    )
    return list(result.scalars().all())


async def create_story_mentions(
    db: AsyncSession,
    story_id: int,
    user_ids: list[int],
) -> None:
    """Insert StoryMention rows for the given user IDs."""
    for uid in user_ids:
        db.add(StoryMention(story_id=story_id, user_id=uid))
    await db.commit()


async def get_story_mentions_batch(
    db: AsyncSession,
    story_ids: list[int],
) -> dict[int, list[MentionedUser]]:
    """Batch-load mentions for a list of stories. Returns {story_id: [MentionedUser]}."""
    if not story_ids:
        return {}
    result = await db.execute(
        select(StoryMention, User)
        .join(User, User.id == StoryMention.user_id)
        .where(StoryMention.story_id.in_(story_ids))
    )
    mentions: dict[int, list[MentionedUser]] = {}
    for sm, user in result.all():
        mentions.setdefault(sm.story_id, []).append(
            MentionedUser(
                user_id=user.id,
                username=user.username,
                avatar_url=user.avatar_url,
            )
        )
    return mentions


def determine_media_type(image_url: str | None, link_url: str | None) -> str:
    """Return the media_type string based on which fields are provided."""
    if image_url and link_url:
        return "link_image"
    if link_url:
        return "link"
    return "image"


def build_link_preview(story: Story) -> LinkPreviewPublic | None:
    """Build a LinkPreviewPublic from a Story's link columns, or None."""
    if not story.link_url:
        return None
    return LinkPreviewPublic(
        url=story.link_url,
        title=story.link_title,
        description=story.link_description,
        image=story.link_image_url,
    )
