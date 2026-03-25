from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import settings

REACTION_TYPES = Literal["agree", "disagree", "love", "misleading"]


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=settings.comment_max_length)
    parent_id: int | None = None


class CommentPublic(BaseModel):
    id: int
    post_id: int
    author_id: int | None
    author_username: str | None = None
    author_avatar_url: str | None = None
    parent_id: int | None
    depth: int
    content: str
    is_removed: bool
    created_at: datetime
    reaction_counts: dict[str, int] = {}
    reply_count: int = 0
    user_reaction: str | None = None

    model_config = {"from_attributes": True}


class ReactionCreate(BaseModel):
    reaction_type: REACTION_TYPES


class ShareCreate(BaseModel):
    comment: str | None = Field(None, max_length=settings.share_comment_max_length)
    community_id: int | None = None
