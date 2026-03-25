from datetime import datetime

from pydantic import BaseModel, Field

# --- Suspensions ---


class SuspensionCreate(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)
    expires_at: datetime | None = None  # None = indefinite until manually lifted


class SuspensionPublic(BaseModel):
    id: int
    user_id: int
    username: str
    suspended_by_id: int
    reason: str
    expires_at: datetime | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Global Bans ---


class GlobalBanCreate(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class GlobalBanPublic(BaseModel):
    id: int
    user_id: int
    username: str
    banned_by_id: int
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Content Removal ---


class ContentRemovalCreate(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class ContentRemovalPublic(BaseModel):
    id: int
    admin_id: int
    content_type: str
    content_id: int
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Reports (admin view) ---


class ReportPublic(BaseModel):
    id: int
    reporter_id: int
    reporter_username: str
    content_type: str
    content_id: int
    reason: str
    status: str
    resolved_by_id: int | None
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportResolve(BaseModel):
    action: str = Field(..., pattern="^(dismiss|remove_content)$")
    reason: str | None = Field(None, max_length=1000)


# --- Admin user listing ---


class AdminUserPublic(BaseModel):
    id: int
    username: str
    email: str
    display_name: str | None
    is_active: bool
    is_verified: bool
    is_admin: bool
    karma: int
    created_at: datetime

    model_config = {"from_attributes": True}
