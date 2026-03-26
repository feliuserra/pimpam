from datetime import datetime

from pydantic import BaseModel

from app.schemas.post import PostPublic


class CuratedPickCreate(BaseModel):
    post_id: int
    note: str | None = None


class CuratedPickPublic(BaseModel):
    id: int
    post_id: int
    community_id: int
    community_name: str = ""
    curator_id: int
    curator_username: str = ""
    note: str | None = None
    created_at: datetime
    post: PostPublic | None = None

    model_config = {"from_attributes": True}
