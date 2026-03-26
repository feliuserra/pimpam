from datetime import datetime

from pydantic import BaseModel, field_validator


class FriendGroupCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Group name cannot be empty")
        return v


class FriendGroupRename(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Group name cannot be empty")
        return v


class FriendGroupMemberAdd(BaseModel):
    user_id: int


class FriendGroupMemberPublic(BaseModel):
    user_id: int
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    added_at: datetime


class FriendGroupPublic(BaseModel):
    id: int
    name: str
    is_close_friends: bool
    member_count: int
    members: list[FriendGroupMemberPublic] = []
    created_at: datetime

    model_config = {"from_attributes": True}
