from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore",
    )

    APP_NAME: str = "media-service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://media_svc:mediapass@media-postgres:5432/mediadb"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://redis:6379/8"

    # Storage
    UPLOADS_BASE_PATH: str = "/app/uploads"
    DOCUMENT_MAX_SIZE_MB: int = 50
    STORAGE_BACKEND: str = "local"  # "local" or "s3"
    AWS_S3_BUCKET: str = ""
    AWS_S3_REGION: str = "us-east-1"
    AWS_S3_ENDPOINT: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Security
    S2S_SERVICE_TOKEN: str = "s2s-change-me-in-production"
    JWT_SECRET: str = "change-me-in-production-min-32-chars!!"
    JWT_ALGORITHM: str = "HS256"
    USER_SERVICE_URL: str = "http://user-api:8001"
    USER_CACHE_TTL: int = 60
    REQUIRE_AUTH: bool = True

    # File upload limits / validation
    ALLOWED_CATEGORIES: list[str] = [
        "documents", "images", "certificates", "evidence", "logos", "avatars", "exports", "general",
    ]
    ALLOWED_MIME_TYPES: list[str] = [
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "application/pdf",
        "text/csv", "text/plain",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
    ]

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"LOG_LEVEL must be one of {valid}")
        return upper

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        import os
        env = os.environ.get("ENV", "dev").lower()
        if env in ("prod", "production"):
            if not v or len(v) < 32 or v.startswith("change-me"):
                raise ValueError(
                    "JWT_SECRET must be set to a strong (>=32 chars) value in production."
                )
        return v

    @field_validator("S2S_SERVICE_TOKEN")
    @classmethod
    def validate_s2s_token(cls, v: str) -> str:
        import os
        env = os.environ.get("ENV", "dev").lower()
        if env in ("prod", "production") and (not v or v.startswith("s2s-change-me")):
            raise ValueError("S2S_SERVICE_TOKEN must be set in production")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
