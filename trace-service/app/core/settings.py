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

    # ─── Solana / Helius ──────────────────────────────────────────────────────
    # CLAUDE.md regla #0.bis: blockchain SIEMPRE real contra devnet/mainnet
    # via Helius. HELIUS_API_KEY y SOLANA_KEYPAIR son OBLIGATORIOS — sin ellos
    # trace-api no arranca (ver provider_factory.get_blockchain_provider).
    SOLANA_NETWORK: Literal["devnet", "mainnet-beta"] = "devnet"
    SOLANA_RPC_URL: str = "https://api.devnet.solana.com"
    SOLANA_KEYPAIR: str = Field(default="", description="base58 keypair (64 bytes) — fee payer")
    SOLANA_COMMITMENT: Literal["processed", "confirmed", "finalized"] = "confirmed"
    SOLANA_TIMEOUT: float = 30.0
    SOLANA_CIRCUIT_BREAKER_THRESHOLD: int = 5
    SOLANA_CIRCUIT_BREAKER_RECOVERY: int = 60  # seconds
    HELIUS_API_KEY: str = ""
    HELIUS_RPC_URL: str = ""  # auto-resolved from SOLANA_NETWORK if empty

    @property
    def effective_helius_rpc_url(self) -> str:
        """Helius RPC URL resolved from network if not explicitly set."""
        if self.HELIUS_RPC_URL:
            return self.HELIUS_RPC_URL
        if self.SOLANA_NETWORK == "mainnet-beta":
            return "https://mainnet.helius-rpc.com"
        return "https://devnet.helius-rpc.com"

    @property
    def effective_solana_rpc_url(self) -> str:
        """Best RPC URL: Helius if available, else SOLANA_RPC_URL."""
        if self.HELIUS_API_KEY:
            return f"{self.effective_helius_rpc_url}/?api-key={self.HELIUS_API_KEY}"
        return self.SOLANA_RPC_URL

    @property
    def blockchain_mode(self) -> str:
        """Current mode: helius | rpc-direct. Simulation removed (CLAUDE.md #0.bis)."""
        if self.HELIUS_API_KEY:
            return "helius"
        return "rpc-direct"

    # ─── Security ─────────────────────────────────────────────────────────────
    TRACE_ADMIN_KEY: str = "change-me-in-production"
    S2S_SERVICE_TOKEN: str = "s2s-change-me-in-production"  # shared secret for inter-service calls
    JWT_SECRET: str = "change-me-in-production-min-32-chars!!"
    # Fernet key for encrypting wallet secret keys at rest. In production must be
    # set to a real Fernet.generate_key() value (validator below enforces this).
    FERNET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    USER_SERVICE_URL: str = "http://user-api:8001"
    USER_CACHE_TTL: int = 60
    # Set to False to require JWT in production. Dev/tests can disable.
    REQUIRE_AUTH: bool = True

    # ─── Subscription / Module gating ──────────────────────────────────────────
    PUBLIC_BASE_URL: str = "http://localhost:8000"  # public-facing URL for metadata URIs
    SUBSCRIPTION_SERVICE_URL: str = "http://subscription-api:8002"
    COMPLIANCE_SERVICE_URL: str = "http://compliance-api:8005"
    MEDIA_SERVICE_URL: str = "http://media-api:8007"
    MODULE_CACHE_TTL: int = 300  # 5 minutes
    MODULE_SLUG: str = "logistics"

    # ─── Media / Storage ─────────────────────────────────────────────────────
    UPLOADS_BASE_PATH: str = "/app/uploads"
    DOCUMENT_MAX_SIZE_MB: int = 20
    STORAGE_BACKEND: str = "local"  # "local" or "s3"
    AWS_S3_BUCKET: str = ""
    AWS_S3_REGION: str = "us-east-1"
    AWS_S3_ENDPOINT: str = ""  # for MinIO or S3-compatible
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

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

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Fail closed: refuse to start in production with a default/short secret."""
        import os
        env = os.environ.get("ENV", "dev").lower()
        if env in ("prod", "production"):
            if not v or len(v) < 32 or v.startswith("change-me"):
                raise ValueError(
                    "JWT_SECRET must be set to a strong (>=32 chars) value in production. "
                    "Default 'change-me-...' values are forbidden."
                )
        return v

    @field_validator("TRACE_ADMIN_KEY")
    @classmethod
    def validate_admin_key(cls, v: str) -> str:
        import os
        env = os.environ.get("ENV", "dev").lower()
        if env in ("prod", "production") and (not v or v.startswith("change-me")):
            raise ValueError("TRACE_ADMIN_KEY must be set in production")
        return v

    @field_validator("REQUIRE_AUTH")
    @classmethod
    def validate_require_auth(cls, v: bool) -> bool:
        """Refuse to start in production with REQUIRE_AUTH=False.
        Setting it False would bypass JWT enforcement and accept any
        X-User-Id/X-Tenant-Id from the client.
        """
        import os
        env = os.environ.get("ENV", "dev").lower()
        if env in ("prod", "production") and v is False:
            raise ValueError("REQUIRE_AUTH must be True in production")
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
                "FERNET_KEY must be set in production for at-rest encryption "
                "of wallet secret keys. Generate with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
