from datetime import datetime

from pydantic import BaseModel


class BlockPublic(BaseModel):
    id: int
    blocker_id: int
    blocked_id: int
    blocked_username: str | None = None
    blocked_avatar_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
