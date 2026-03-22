from datetime import datetime

from pydantic import BaseModel, model_validator


class PostCreate(BaseModel):
    title: str
    content: str | None = None
    url: str | None = None
    community_id: int | None = None

    @model_validator(mode="after")
    def must_have_content_or_url(self) -> "PostCreate":
        if not self.content and not self.url:
            raise ValueError("Post must have either content or a URL")
        return self


class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    url: str | None = None


class PostPublic(BaseModel):
    id: int
    title: str
    content: str | None
    url: str | None
    author_id: int
    community_id: int | None
    karma: int
    is_edited: bool
    edited_at: datetime | None
    is_removed: bool
    created_at: datetime

    model_config = {"from_attributes": True}
