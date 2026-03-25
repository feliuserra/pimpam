from datetime import datetime

from pydantic import BaseModel, field_validator


class CommunityCreate(BaseModel):
    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Community name may only contain letters, numbers, hyphens, and underscores"
            )
        if len(v) < 3 or len(v) > 100:
            raise ValueError("Community name must be between 3 and 100 characters")
        return v.lower()


class CommunityPublic(BaseModel):
    id: int
    name: str
    description: str | None
    owner_id: int
    member_count: int
    is_news: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class CommunityKarmaPublic(BaseModel):
    """A user's karma score within a specific community."""

    community_id: int
    user_id: int
    karma: int
    role: str

    model_config = {"from_attributes": True}
