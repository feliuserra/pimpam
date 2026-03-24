from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: str | None = None

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may only contain letters, numbers, hyphens, and underscores")
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be between 3 and 50 characters")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserUpdate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None


class UserPublic(BaseModel):
    id: int
    username: str
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    karma: int
    is_verified: bool
    deletion_scheduled_at: datetime | None = None
    created_at: datetime
    follower_count: int = 0
    following_count: int = 0
    is_following: bool | None = None  # None on own profile or unauthenticated

    model_config = {"from_attributes": True}


class DeleteAccountRequest(BaseModel):
    password: str = Field(..., min_length=1)


class UserLogin(BaseModel):
    username: str
    password: str
    totp_code: str | None = None  # required when the account has 2FA enabled


class TotpSetupResponse(BaseModel):
    """Returned by POST /auth/totp/setup. Client renders `uri` as a QR code."""
    uri: str     # otpauth:// provisioning URI
    secret: str  # raw base32 secret for manual entry in authenticator apps


class TotpVerifyRequest(BaseModel):
    code: str  # 6-digit code from authenticator app


class TotpDisableRequest(BaseModel):
    password: str  # current account password
    code: str      # current valid TOTP code
