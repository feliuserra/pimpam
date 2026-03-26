"""
Ephemeral stories — image, link, or both + optional caption, user-chosen duration.

Design constraints (per CLAUDE.md):
  - No "seen by" tracking. Views are never recorded.
  - No expiry timestamp in responses (prevents countdown UI).
  - Reported stories are soft-deleted and retained 48 h for mod review.
  - Hourly cleanup task (app/main.py) hard-deletes expired non-reported stories.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import or_, select

from app.core.config import settings
from app.core.dependencies import CurrentUser, DBSession
from app.core.limiter import limiter
from app.core.og_parser import fetch_og_metadata
from app.crud.notification import notify
from app.crud.story import (
    build_link_preview,
    create_story,
    create_story_mentions,
    determine_media_type,
    extract_mentions,
    get_story_mentions_batch,
    resolve_mentions,
)
from app.models.community import CommunityMember
from app.models.follow import Follow
from app.models.story import Story
from app.models.user import User
from app.schemas.story import StoryCreate, StoryPublic

router = APIRouter(prefix="/stories", tags=["stories"])


def _story_to_public(
    story: Story,
    username: str,
    avatar_url: str | None,
    mentions: list | None = None,
) -> StoryPublic:
    """Build a StoryPublic from a Story + author info."""
    return StoryPublic(
        id=story.id,
        author_id=story.author_id,
        author_username=username,
        author_avatar_url=avatar_url,
        media_type=story.media_type,
        image_url=story.image_url,
        caption=story.caption,
        link_preview=build_link_preview(story),
        mentions=mentions or [],
        created_at=story.created_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=StoryPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour")
async def create_story_endpoint(
    request: Request,
    data: StoryCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Create a story. Images must already be uploaded via POST /media/upload.
    Provide image_url, link_url, or both. duration_hours: 12, 24, 48, 168.
    Mentions (@username) in the caption will notify tagged users.
    """
    media_type = determine_media_type(data.image_url, data.link_url)

    # Fetch OG metadata for link stories
    link_title = link_description = link_image_url = None
    if data.link_url:
        og = await fetch_og_metadata(data.link_url)
        link_title = og.get("title")
        link_description = og.get("description")
        link_image_url = og.get("image")

    story = await create_story(
        db,
        author_id=current_user.id,
        media_type=media_type,
        image_url=data.image_url,
        caption=data.caption,
        duration_hours=data.duration_hours,
        link_url=data.link_url,
        link_title=link_title,
        link_description=link_description,
        link_image_url=link_image_url,
    )

    # Process @mentions in caption
    mention_list = []
    if data.caption:
        usernames = extract_mentions(data.caption)
        if usernames:
            users = await resolve_mentions(db, usernames, settings.story_max_mentions)
            if users:
                await create_story_mentions(db, story.id, [u.id for u in users])
                for u in users:
                    await notify(
                        db,
                        u.id,
                        "story_mention",
                        actor_id=current_user.id,
                        story_id=story.id,
                    )
                from app.schemas.story import MentionedUser

                mention_list = [
                    MentionedUser(
                        user_id=u.id,
                        username=u.username,
                        avatar_url=u.avatar_url,
                    )
                    for u in users
                ]

    return _story_to_public(
        story, current_user.username, current_user.avatar_url, mention_list
    )


@router.get("/feed", response_model=list[StoryPublic])
@limiter.limit("60/minute")
async def get_stories_feed(
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
    limit: int = Query(default=50, le=100),
):
    """
    Stories from users the viewer follows + communities they have joined,
    not yet expired, ordered newest first.

    The expiry timestamp is intentionally NOT included in the response
    to prevent countdown UI on the frontend.
    """
    now = datetime.now(timezone.utc)

    followed_ids = select(Follow.followed_id).where(
        Follow.follower_id == current_user.id,
        Follow.is_pending == False,  # noqa: E712
    )
    joined_community_ids = select(CommunityMember.community_id).where(
        CommunityMember.user_id == current_user.id
    )
    community_member_ids = select(CommunityMember.user_id).where(
        CommunityMember.community_id.in_(joined_community_ids)
    )

    result = await db.execute(
        select(Story, User)
        .join(User, User.id == Story.author_id)
        .where(
            or_(
                Story.author_id.in_(followed_ids),
                Story.author_id.in_(community_member_ids),
            ),
            Story.expires_at > now,
            Story.is_removed == False,  # noqa: E712
            Story.author_id != current_user.id,
        )
        .order_by(Story.created_at.desc())
        .limit(limit)
    )

    rows = result.all()

    # Batch-load mentions to avoid N+1
    story_ids = [story.id for story, _ in rows]
    mentions_map = await get_story_mentions_batch(db, story_ids)

    return [
        _story_to_public(
            story,
            user.username,
            user.avatar_url,
            mentions_map.get(story.id, []),
        )
        for story, user in rows
    ]


@router.get("/me", response_model=list[StoryPublic])
@limiter.limit("60/minute")
async def get_my_stories(
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
):
    """Return the current user's own active (non-expired) stories."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Story)
        .where(
            Story.author_id == current_user.id,
            Story.expires_at > now,
            Story.is_removed == False,  # noqa: E712
        )
        .order_by(Story.created_at.desc())
    )
    stories = list(result.scalars().all())

    story_ids = [s.id for s in stories]
    mentions_map = await get_story_mentions_batch(db, story_ids)

    return [
        _story_to_public(
            s,
            current_user.username,
            current_user.avatar_url,
            mentions_map.get(s.id, []),
        )
        for s in stories
    ]


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_story(
    story_id: int,
    current_user: CurrentUser,
    db: DBSession,
):
    """Delete your own story before it expires."""
    result = await db.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    if story is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    if story.author_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your story")
    await db.delete(story)
    await db.commit()


@router.post("/{story_id}/report", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def report_story(
    request: Request,
    story_id: int,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Report a story. The story is immediately soft-deleted (hidden from all viewers)
    but retained in the database for 48 h so moderators can review it.
    The hourly cleanup task skips soft-deleted stories.
    """
    result = await db.execute(
        select(Story).where(Story.id == story_id, Story.is_removed == False)  # noqa: E712
    )
    story = result.scalar_one_or_none()
    if story is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    story.is_removed = True
    await db.commit()
