import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

VALID_LAYOUT_SECTIONS = {"bio", "pinned_post", "community_stats"}


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: str | None = None

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username may only contain letters, numbers, hyphens, and underscores"
            )
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
    cover_image_url: str | None = None
    accent_color: str | None = None
    location: str | None = None
    website: str | None = None
    pronouns: str | None = None
    profile_layout: list[str] | None = None
    show_community_stats: bool | None = None
    show_posts_on_profile: bool | None = None
    cover_gradient: bool | None = None

    @field_validator("accent_color")
    @classmethod
    def validate_accent_color(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not re.match(r"^#[0-9a-fA-F]{6}$", v):
            raise ValueError("Accent color must be a hex color like #ff5500")
        # Reject colors that are too light (luminance > 0.9)
        r, g, b = int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        if luminance > 0.9:
            raise ValueError("Accent color is too light to be readable")
        return v.lower()

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not v.startswith(("http://", "https://")):
            raise ValueError("Website must start with http:// or https://")
        return v

    @field_validator("profile_layout")
    @classmethod
    def validate_profile_layout(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        if len(v) != len(set(v)):
            raise ValueError("Profile layout must not contain duplicates")
        invalid = set(v) - VALID_LAYOUT_SECTIONS
        if invalid:
            raise ValueError(
                f"Invalid layout sections: {invalid}. Allowed: {VALID_LAYOUT_SECTIONS}"
            )
        return v


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
    cover_image_url: str | None = None
    accent_color: str | None = None
    location: str | None = None
    website: str | None = None
    pronouns: str | None = None
    pinned_post_id: int | None = None
    profile_layout: list[str] | None = None
    show_community_stats: bool = True
    show_posts_on_profile: bool = True
    cover_gradient: bool = True
    is_admin: bool = False

    model_config = {"from_attributes": True}

    @field_validator("profile_layout", mode="before")
    @classmethod
    def parse_profile_layout(cls, v: str | list | None) -> list[str] | None:
        """Deserialize JSON string from DB into a list."""
        if v is None:
            return None
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v


class CommunityStatsPublic(BaseModel):
    joined: int = 0
    moderating: int = 0
    owned: int = 0


class DeleteAccountRequest(BaseModel):
    password: str = Field(..., min_length=1)


class UserLogin(BaseModel):
    username: str
    password: str
    totp_code: str | None = None  # required when the account has 2FA enabled


class TotpSetupResponse(BaseModel):
    """Returned by POST /auth/totp/setup. Client renders `uri` as a QR code."""

    uri: str  # otpauth:// provisioning URI
    secret: str  # raw base32 secret for manual entry in authenticator apps


class TotpVerifyRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")  # 6-digit code from authenticator app


class TotpDisableRequest(BaseModel):
    password: str  # current account password
    code: str  # current valid TOTP code
