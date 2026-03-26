from datetime import datetime

from pydantic import BaseModel


class HashtagSubscriptionPublic(BaseModel):
    id: int
    hashtag_id: int
    hashtag_name: str
    subscribed_at: datetime

    model_config = {"from_attributes": True}
