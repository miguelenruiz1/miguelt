from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")

    APP_NAME: str = "ai-service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql+asyncpg://ai_svc:aipass@ai-postgres:5432/aidb"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False

    REDIS_URL: str = "redis://redis:6379/7"

    USER_SERVICE_URL: str = "http://user-api:8001"
    INVENTORY_SERVICE_URL: str = "http://inventory-api:8003"
    JWT_SECRET: str = "change-me-in-production-min-32-chars!!"
    JWT_ALGORITHM: str = "HS256"
    USER_CACHE_TTL: int = 60

    S2S_SERVICE_TOKEN: str = "s2s-change-me-in-production"

    ANTHROPIC_API_KEY: str = ""
    AI_ANALYSIS_DAILY_LIMIT: int = 10

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
                raise ValueError("JWT_SECRET must be set to a >=32 char strong value in production.")
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
