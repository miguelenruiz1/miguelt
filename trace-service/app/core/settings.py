from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ─── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "trace-service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ─── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://trace:tracepass@postgres:5432/tracedb"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False

    # ─── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"
    ARQ_REDIS_URL: str = "redis://redis:6379/1"
    IDEMPOTENCY_TTL: int = 86400  # 24h in seconds

    # ─── Solana ───────────────────────────────────────────────────────────────
    SOLANA_RPC_URL: str = "https://api.devnet.solana.com"
    SOLANA_KEYPAIR: str = Field(default="", description="base58 keypair or file path")
    SOLANA_SIMULATION: bool = True
    SOLANA_COMMITMENT: Literal["processed", "confirmed", "finalized"] = "confirmed"
    SOLANA_TIMEOUT: float = 30.0
    SOLANA_CIRCUIT_BREAKER_THRESHOLD: int = 5
    SOLANA_CIRCUIT_BREAKER_RECOVERY: int = 60  # seconds

    # ─── Helius ───────────────────────────────────────────────────────────────
    HELIUS_API_KEY: str = ""           # empty = use SimulationProvider
    HELIUS_RPC_URL: str = "https://devnet.helius-rpc.com"
    HELIUS_NETWORK: str = "devnet"     # devnet | mainnet-beta

    # ─── Security ─────────────────────────────────────────────────────────────
    TRACE_ADMIN_KEY: str = "change-me-in-production"

    # ─── Subscription / Module gating ──────────────────────────────────────────
    SUBSCRIPTION_SERVICE_URL: str = "http://subscription-api:8002"
    MODULE_CACHE_TTL: int = 300  # 5 minutes
    MODULE_SLUG: str = "logistics"

    # ─── Worker / Anchor ──────────────────────────────────────────────────────
    ANCHOR_MAX_RETRIES: int = 5
    ANCHOR_RETRY_DELAY: float = 2.0
    ANCHOR_QUEUE_NAME: str = "anchor"

    # ─── Postgres (for compose) ───────────────────────────────────────────────
    POSTGRES_USER: str = "trace"
    POSTGRES_PASSWORD: str = "tracepass"
    POSTGRES_DB: str = "tracedb"

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
