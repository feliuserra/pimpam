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
    cors_origins: list[str] = ["http://localhost:5173"]

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
    storage_region: str = "auto"           # R2 uses "auto"; AWS uses e.g. "us-east-1"
    storage_public_url: str = "http://localhost:9000/pimpam"  # base URL for serving files
    storage_enabled: bool = True

    # Real-time (Redis pub/sub for WebSocket fan-out)
    redis_url: str = "redis://localhost:6379"

    # Search (Meilisearch)
    search_url: str = "http://localhost:7700"
    search_api_key: str = ""   # leave blank for local dev; set a master key in prod
    search_enabled: bool = True

    # Media limits
    media_max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    media_avatar_max_px: int = 512                   # avatars are capped at 512×512
    media_post_image_max_px: int = 2000              # post images capped at 2000px on longest side


settings = Settings()
