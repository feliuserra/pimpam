from datetime import datetime

from pydantic import BaseModel


class NotificationPublic(BaseModel):
    id: int
    user_id: int
    type: str
    actor_id: int | None
    actor_username: str | None = None
    actor_avatar_url: str | None = None
    post_id: int | None
    comment_id: int | None
    community_id: int | None
    story_id: int | None = None
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


class NotificationIds(BaseModel):
    ids: list[int]
