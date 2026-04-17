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
    MEDIA_SERVICE_URL: str = "http://media-api:8007"
    USER_SERVICE_URL: str = "http://user-api:8001"

    JWT_SECRET: str = "super-secret-dev-key-change-in-prod"
    JWT_ALGORITHM: str = "HS256"
    USER_CACHE_TTL: int = 60
    S2S_SERVICE_TOKEN: str = "s2s-change-me-in-production"

    # Dedicated key for encrypting integration credentials.
    # If empty, derives one from JWT_SECRET (insecure for prod — set explicitly).
    FERNET_KEY: str = ""

    MODULE_SLUG: str = "compliance"
    MODULE_CACHE_TTL: int = 300

    # Public URLs
    PUBLIC_BASE_URL: str = "http://localhost:9005"
    SOLANA_NETWORK: str = "devnet"

    # Global Forest Watch (deforestation screening)
    GFW_API_KEY: str = ""  # Get free at https://www.globalforestwatch.org/my-gfw/

    # TRACES NT (EU DDS submission)
    TRACES_NT_USERNAME: str = ""
    TRACES_NT_AUTH_KEY: str = ""
    TRACES_NT_ENV: str = "acceptance"  # acceptance | production
    TRACES_NT_CLIENT_ID: str = "eudr-test"  # webServiceClientId assigned by EU
    TRACES_NT_TIMEOUT: float = 180.0
    GFW_TIMEOUT: float = 120.0

    # Certificate generation
    CERTIFICATE_STORAGE: str = "local"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = "tracelog-certificates"
    AWS_REGION: str = "us-east-1"
    TRACELOG_LOGO_URL: str = ""

    @property
    def CERTIFICATE_VERIFY_BASE_URL(self) -> str:
        return f"{self.PUBLIC_BASE_URL}/api/v1/compliance/verify"

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
        # Blocklist covers both shapes of placeholder secrets this repo has
        # shipped with. Previously only `change-me` was checked, which let
        # `super-secret-dev-key-change-in-prod` (the compose default here)
        # sneak through a production deploy silently.
        insecure_prefixes = ("change-me", "super-secret-dev", "dev-secret", "test-secret")
        if env in ("prod", "production"):
            if not v or len(v) < 32 or v.startswith(insecure_prefixes):
                raise ValueError("JWT_SECRET must be set to >=32 char strong value in production.")
        return v

    @field_validator("S2S_SERVICE_TOKEN")
    @classmethod
    def validate_s2s_token(cls, v: str) -> str:
        import os
        env = os.environ.get("ENV", "dev").lower()
        if env in ("prod", "production") and (not v or v.startswith("s2s-change-me")):
            raise ValueError("S2S_SERVICE_TOKEN must be set in production")
        return v

    @field_validator("FERNET_KEY")
    @classmethod
    def validate_fernet_key(cls, v: str) -> str:
        import os
        env = os.environ.get("ENV", "dev").lower()
        if env in ("prod", "production") and not v:
            raise ValueError(
                "FERNET_KEY must be set in production. Generate with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
