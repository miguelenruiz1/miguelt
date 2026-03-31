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

    APP_NAME: str = "inventory-service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql+asyncpg://inv_svc:invpass@inventory-postgres:5432/inventorydb"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False

    REDIS_URL: str = "redis://redis:6379/4"

    UPLOAD_DIR: str = "/app/uploads"
    MAX_IMAGE_SIZE: int = 5 * 1024 * 1024  # 5 MB

    USER_SERVICE_URL: str = "http://user-api:8001"
    SUBSCRIPTION_SERVICE_URL: str = "http://subscription-api:8002"
    INTEGRATION_SERVICE_URL: str = "http://integration-api:8004"
    JWT_SECRET: str = "change-me-in-production-min-32-chars!!"
    S2S_SERVICE_TOKEN: str = "s2s-change-me-in-production"  # shared secret for inter-service calls
    TRACE_SERVICE_URL: str = "http://trace-api:8000"
    MEDIA_SERVICE_URL: str = "http://media-api:8007"
    INTEGRATION_SERVICE_URL: str = "http://integration-api:8004"
    JWT_ALGORITHM: str = "HS256"
    USER_CACHE_TTL: int = 60
    MODULE_CACHE_TTL: int = 300
    MODULE_SLUG: str = "inventory"

    # ─── AI Service ──────────────────────────────────────────────────────
    AI_SERVICE_URL: str = "http://ai-api:8006"


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
