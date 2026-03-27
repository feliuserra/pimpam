from datetime import datetime

from pydantic import BaseModel, Field, model_validator

# --- Poll schemas ---


class PollOptionCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=200)


class PollCreate(BaseModel):
    question: str = Field(..., min_length=1, max_length=300)
    options: list[PollOptionCreate] = Field(..., min_length=2, max_length=10)
    allows_multiple: bool = False

    @model_validator(mode="after")
    def no_duplicate_options(self) -> "PollCreate":
        texts = [o.text.strip().lower() for o in self.options]
        if len(texts) != len(set(texts)):
            raise ValueError("Poll options must be unique")
        return self


class PollOptionPublic(BaseModel):
    id: int
    text: str
    vote_count: int
    display_order: int

    model_config = {"from_attributes": True}


class PollPublic(BaseModel):
    id: int
    question: str
    allows_multiple: bool
    options: list[PollOptionPublic] = []
    total_votes: int = 0
    user_voted_option_ids: list[int] = []


# --- Issue schemas ---


class IssueCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    category: str = Field(
        ..., pattern="^(bug|feature|improvement|suggestion|complaint)$"
    )
    device_info: str | None = Field(None, max_length=500)
    poll: PollCreate | None = None


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
    is_closed: bool = False
    closed_at: datetime | None = None
    has_voted: bool = False  # whether the current user has voted
    poll: PollPublic | None = None
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


class PollVoteRequest(BaseModel):
    option_id: int
