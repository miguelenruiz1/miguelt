from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ─── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "user-service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ─── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://user_svc:userpass@user-postgres:5432/userdb"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False

    # ─── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/2"

    # ─── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET: str = "change-me-in-production-min-32-chars!!"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── SMTP ─────────────────────────────────────────────────────────────────
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@trace.app"
    SMTP_USE_TLS: bool = False
    # Platform-level email provider (overrides tenant config)
    RESEND_API_KEY: str = ""  # If set, all emails go via Resend. Empty = use SMTP/Mailhog

    # ─── Uploads ───────────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "/app/uploads"
    MEDIA_SERVICE_URL: str = "http://media-api:8007"
    S2S_SERVICE_TOKEN: str = "s2s-change-me-in-production"
    MAX_AVATAR_SIZE: int = 2 * 1024 * 1024  # 2 MB

    # ─── Inter-service ─────────────────────────────────────────────────────────
    SUBSCRIPTION_SERVICE_URL: str = "http://subscription-api:8002"

    # ─── Frontend ─────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"LOG_LEVEL must be one of {valid}")
        return upper


@lru_cache
def get_settings() -> Settings:
    return Settings()
