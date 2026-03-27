from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql+asyncpg://pimpam:pimpam@localhost:5432/pimpam"

    # Auth
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    # Separate key for AES (Fernet) encryption of TOTP secrets at rest.
    # Rotate independently of secret_key so JWT rotation doesn't lock users out of 2FA.
    # Generate: python -c "import secrets; print(secrets.token_hex(32))"
    encryption_key: str = "change-me-in-production"

    # CORS — in production, set to your actual frontend origin
    cors_origins: list[str] = [
        "http://localhost:5173",
        "capacitor://localhost",
        "http://localhost",
    ]

    # App
    environment: str = "development"
    app_name: str = "PimPam"
    app_version: str = "0.1.0"

    # Federation (ActivityPub)
    # Set DOMAIN to your public hostname (e.g. "pimpam.social") to enable federation.
    domain: str = "localhost:8000"
    federation_enabled: bool = True
    remote_actor_cache_ttl_seconds: int = 86400  # 24 hours

    # Storage (S3-compatible — MinIO in dev, Cloudflare R2 in prod)
    # Leave storage_endpoint_url empty to disable media uploads.
    storage_endpoint_url: str = "http://localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket: str = "pimpam"
    storage_region: str = "auto"  # R2 uses "auto"; AWS uses e.g. "us-east-1"
    storage_public_url: str = (
        "http://localhost:9000/pimpam"  # base URL for serving files
    )
    storage_enabled: bool = True

    # Real-time (Redis pub/sub for WebSocket fan-out)
    redis_url: str = "redis://localhost:6379"

    # Search (Meilisearch)
    search_url: str = "http://localhost:7700"
    search_api_key: str = ""  # leave blank for local dev; set a master key in prod
    search_enabled: bool = True

    # Media limits
    media_max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    media_avatar_max_px: int = 512  # avatars are capped at 512×512
    media_post_image_max_px: int = 2000  # post images capped at 2000px on longest side
    media_thumb_max_px: int = 400  # thumbnail variant
    media_medium_max_px: int = 1000  # medium variant (desktop feeds)

    # Storage quotas & signed URLs
    storage_signed_url_ttl: int = 3600  # 1-hour signed URLs
    storage_user_quota_bytes: int = 500 * 1024 * 1024  # 500 MB per user

    # Content limits — change here to affect comments and share annotations everywhere
    comment_max_length: int = 300
    share_comment_max_length: int = 300

    # Reaction karma values — positive reactions add, negative subtract from commenter's global karma
    reaction_karma: dict[str, int] = {
        "agree": 1,
        "love": 2,
        "disagree": 0,  # never affects karma directly; requires an accompanying reply
        "misleading": -2,
    }

    # Rate limits (counts per day) for reactions that need a cap
    disagree_daily_limit: int = 10

    # SMTP (password reset emails)
    # Set smtp_enabled=true and fill in credentials to enable email delivery.
    smtp_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@pimpam.social"
    smtp_tls: bool = True

    # Password reset token lifetimes and per-email rate cap
    password_reset_link_expire_minutes: int = 15
    password_reset_code_expire_minutes: int = 10
    password_reset_max_requests_per_hour: int = 3

    # Email verification
    email_verification_token_expire_minutes: int = 60
    unverified_account_delete_days: int = 30

    # Account deletion grace period
    account_deletion_grace_days: int = 7

    # Multi-image posts
    multi_image_posts_enabled: bool = False
    post_max_images: int = 10

    # Stories
    story_max_mentions: int = 5
    story_link_preview_timeout: float = 5.0

    # Video stories (future — placeholders only)
    video_enabled: bool = False
    video_max_duration_seconds: int = 10
    video_max_upload_bytes: int = 50 * 1024 * 1024  # 50 MB

    def model_post_init(self, __context) -> None:
        if self.environment != "development":
            if self.secret_key == "change-me-in-production":
                raise SystemExit("FATAL: SECRET_KEY must be changed in production")
            if self.encryption_key == "change-me-in-production":
                raise SystemExit("FATAL: ENCRYPTION_KEY must be changed in production")


settings = Settings()
