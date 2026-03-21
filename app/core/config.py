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


settings = Settings()
