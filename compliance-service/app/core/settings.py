from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore",
    )

    APP_NAME: str = "compliance-service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql+asyncpg://cmp_svc:cmppass@compliance-postgres:5432/compliancedb"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False

    REDIS_URL: str = "redis://redis:6379/5"

    SUBSCRIPTION_SERVICE_URL: str = "http://subscription-api:8002"
    TRACE_SERVICE_URL: str = "http://trace-api:8000"
    USER_SERVICE_URL: str = "http://user-api:8001"

    JWT_SECRET: str = "super-secret-dev-key-change-in-prod"
    JWT_ALGORITHM: str = "HS256"
    USER_CACHE_TTL: int = 60

    MODULE_SLUG: str = "compliance"
    MODULE_CACHE_TTL: int = 300

    # Certificate generation
    CERTIFICATE_STORAGE: str = "local"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = "tracelog-certificates"
    AWS_REGION: str = "us-east-1"
    CERTIFICATE_VERIFY_BASE_URL: str = "http://localhost:9005/api/v1/compliance/verify"
    TRACELOG_LOGO_URL: str = ""

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
