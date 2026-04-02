from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.moderation import CoCViolation


class BanProposalCreate(BaseModel):
    target_username: str = Field(max_length=30)
    reason: str = Field(min_length=1, max_length=2000)
    coc_violation: CoCViolation
    is_permanent: bool = True
    expires_at: datetime | None = None


class BanProposalPublic(BaseModel):
    id: int
    community_id: int
    target_user_id: int
    proposed_by_id: int
    reason: str
    coc_violation: str
    is_permanent: bool
    expires_at: datetime | None
    vote_count: int
    required_votes: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BanPublic(BaseModel):
    id: int
    community_id: int
    user_id: int
    reason: str
    coc_violation: str
    is_permanent: bool
    expires_at: datetime | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ModProposalCreate(BaseModel):
    target_username: str = Field(max_length=30)
    target_role: Literal["moderator", "senior_mod"] = "moderator"


class ModProposalPublic(BaseModel):
    id: int
    community_id: int
    target_user_id: int
    proposed_by_id: int
    vote_count: int
    required_votes: int
    status: str
    target_role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BanAppealCreate(BaseModel):
    ban_id: int
    reason: str = Field(min_length=1, max_length=2000)


class BanAppealPublic(BaseModel):
    id: int
    ban_id: int
    appellant_id: int
    reason: str
    status: str
    vote_count: int
    required_votes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class OwnershipTransferCreate(BaseModel):
    recipient_username: str


class OwnershipTransferPublic(BaseModel):
    id: int
    community_id: int
    proposed_by_id: int
    recipient_id: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OwnershipTransferResponse(BaseModel):
    accept: bool


class CommunityKarmaPublic(BaseModel):
    community_id: int
    community_name: str
    karma: int
    role: str
