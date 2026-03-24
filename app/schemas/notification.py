from datetime import datetime

from pydantic import BaseModel


class NotificationPublic(BaseModel):
    id: int
    user_id: int
    type: str
    actor_id: int | None
    post_id: int | None
    comment_id: int | None
    community_id: int | None
    group_key: str | None
    group_count: int
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PreferenceUpdate(BaseModel):
    notification_type: str
    enabled: bool


class UnreadCount(BaseModel):
    count: int
