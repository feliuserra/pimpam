from datetime import datetime

from pydantic import BaseModel


class HashtagPublic(BaseModel):
    id: int
    name: str
    post_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
