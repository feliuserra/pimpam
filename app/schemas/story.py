"""Pydantic schemas for stories."""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class StoryCreate(BaseModel):
    image_url: str | None = Field(default=None, max_length=500)
    link_url: str | None = Field(default=None, max_length=2048)
    caption: str | None = Field(default=None, max_length=200)
    duration_hours: int = Field(default=24)
    visibility: str = Field(default="close_friends")

    @model_validator(mode="after")
    def must_have_content(self) -> "StoryCreate":
        if not self.image_url and not self.link_url:
            raise ValueError("Story must have an image or a link")
        if self.visibility not in ("close_friends", "followers", "public"):
            raise ValueError(
                "visibility must be 'close_friends', 'followers', or 'public'"
            )
        return self


class MentionedUser(BaseModel):
    user_id: int
    username: str
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


class LinkPreviewPublic(BaseModel):
    url: str
    title: str | None = None
    description: str | None = None
    image: str | None = None

    model_config = {"from_attributes": True}


class StoryPublic(BaseModel):
    id: int
    author_id: int
    author_username: str
    author_avatar_url: str | None = None
    media_type: str
    image_url: str | None = None
    caption: str | None = None
    link_preview: LinkPreviewPublic | None = None
    visibility: str = "close_friends"
    mentions: list[MentionedUser] = []
    created_at: datetime

    model_config = {"from_attributes": True}
