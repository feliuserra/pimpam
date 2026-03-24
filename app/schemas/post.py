from datetime import datetime
from typing import Literal

from pydantic import BaseModel, model_validator


class PostCreate(BaseModel):
    title: str
    content: str | None = None
    url: str | None = None        # external link
    image_url: str | None = None  # single uploaded image (backward compat)
    image_urls: list[str] = []    # multi-image; takes precedence over image_url when non-empty
    community_id: int | None = None
    visibility: Literal["public", "group"] = "public"
    friend_group_id: int | None = None

    @model_validator(mode="after")
    def must_have_content_or_url(self) -> "PostCreate":
        has_image = bool(self.image_url or self.image_urls)
        if not self.content and not self.url and not has_image:
            raise ValueError("Post must have content, a URL, or an image")
        if self.visibility == "group" and self.friend_group_id is None:
            raise ValueError("friend_group_id is required when visibility is 'group'")
        if self.community_id is not None and self.visibility != "public":
            raise ValueError("Community posts must have public visibility")
        return self


class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    url: str | None = None
    image_url: str | None = None


class PostImagePublic(BaseModel):
    url: str
    display_order: int

    model_config = {"from_attributes": True}


class PostPublic(BaseModel):
    id: int
    title: str
    content: str | None
    url: str | None
    image_url: str | None
    images: list[PostImagePublic] = []
    author_id: int | None
    community_id: int | None
    karma: int
    is_edited: bool
    edited_at: datetime | None
    is_removed: bool
    created_at: datetime
    shared_from_id: int | None = None
    share_comment: str | None = None
    visibility: str = "public"
    friend_group_id: int | None = None

    model_config = {"from_attributes": True}
