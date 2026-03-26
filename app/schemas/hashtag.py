from datetime import datetime

from pydantic import BaseModel


class HashtagPublic(BaseModel):
    id: int
    name: str
    post_count: int
    subscriber_count: int = 0
    is_subscribed: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}
