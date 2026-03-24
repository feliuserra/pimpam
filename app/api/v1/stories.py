"""
Ephemeral stories — image + optional caption, user-chosen duration.

Design constraints (per CLAUDE.md):
  - No "seen by" tracking. Views are never recorded.
  - No expiry timestamp in responses (prevents countdown UI).
  - Reported stories are soft-deleted and retained 48 h for mod review.
  - Hourly cleanup task (app/main.py) hard-deletes expired non-reported stories.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select

from app.core.dependencies import CurrentUser, DBSession
from app.core.limiter import limiter
from app.models.community import CommunityMember
from app.models.follow import Follow
from app.models.story import Story
from app.models.user import User

router = APIRouter(prefix="/stories", tags=["stories"])

ALLOWED_DURATIONS = {12, 24, 48, 168}  # hours


# ---------------------------------------------------------------------------
# Schemas (inline — simple enough not to need a separate file)
# ---------------------------------------------------------------------------

class StoryCreate(BaseModel):
    image_url: str = Field(..., max_length=500)
    caption: str | None = Field(default=None, max_length=200)
    duration_hours: int = Field(default=24)


class StoryPublic(BaseModel):
    id: int
    author_id: int
    author_username: str
    author_avatar_url: str | None
    image_url: str
    caption: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=StoryPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour")
async def create_story(
    request: Request,
    data: StoryCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Create a story. The image must already be uploaded via POST /media/upload.
    duration_hours must be one of: 12, 24, 48, 168 (7 days). Default: 24.
    """
    duration = data.duration_hours if data.duration_hours in ALLOWED_DURATIONS else 24
    story = Story(
        author_id=current_user.id,
        image_url=data.image_url,
        caption=data.caption,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=duration),
    )
    db.add(story)
    await db.commit()
    await db.refresh(story)
    return StoryPublic(
        id=story.id,
        author_id=story.author_id,
        author_username=current_user.username,
        author_avatar_url=current_user.avatar_url,
        image_url=story.image_url,
        caption=story.caption,
        created_at=story.created_at,
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
    # Authors of posts in joined communities (stories don't belong to communities,
    # so we include stories from members of the same communities)
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
            Story.author_id != current_user.id,  # own stories shown separately
        )
        .order_by(Story.created_at.desc())
        .limit(limit)
    )

    rows = result.all()
    return [
        StoryPublic(
            id=story.id,
            author_id=story.author_id,
            author_username=user.username,
            author_avatar_url=user.avatar_url,
            image_url=story.image_url,
            caption=story.caption,
            created_at=story.created_at,
        )
        for story, user in rows
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
