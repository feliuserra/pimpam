from datetime import datetime

from pydantic import BaseModel, Field


class IssueCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    category: str = Field(
        ..., pattern="^(bug|feature|improvement|suggestion|complaint)$"
    )
    device_info: str | None = Field(None, max_length=500)


class IssueUpdate(BaseModel):
    """Admin-only updates: status and security flag."""

    status: str | None = Field(None, pattern="^(open|in_progress|completed|rejected)$")
    is_security: bool | None = None


class IssuePublic(BaseModel):
    id: int
    author_id: int
    author_username: str
    title: str
    description: str
    category: str
    status: str
    vote_count: int
    comment_count: int
    device_info: str | None = None
    is_security: bool
    has_voted: bool = False  # whether the current user has voted
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IssueCommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class IssueCommentPublic(BaseModel):
    id: int
    issue_id: int
    author_id: int
    author_username: str
    is_admin: bool = False
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
