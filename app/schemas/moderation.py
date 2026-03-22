from datetime import datetime

from pydantic import BaseModel

from app.models.moderation import CoCViolation


class BanProposalCreate(BaseModel):
    target_username: str
    reason: str
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
    created_at: datetime

    model_config = {"from_attributes": True}


class ModProposalCreate(BaseModel):
    target_username: str


class ModProposalPublic(BaseModel):
    id: int
    community_id: int
    target_user_id: int
    proposed_by_id: int
    vote_count: int
    required_votes: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
