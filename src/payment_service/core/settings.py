"""Application settings loaded from environment variables / .env file.

Uses pydantic-settings v2 for type-safe, validated configuration.
All values can be overridden via environment variables (case-insensitive).
"""

from functools import lru_cache

from pydantic import AmqpDsn, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object for the payment service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "payment-service"
    debug: bool = False
    api_key: SecretStr  # Static API key for X-API-Key authentication

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: PostgresDsn
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    # ── RabbitMQ ──────────────────────────────────────────────────────────────
    rabbitmq_url: AmqpDsn

    # Queue / exchange names
    payments_exchange: str = "payments"
    payments_new_queue: str = "payments.new"
    payments_dlq: str = "payments.new.dlq"
    payments_dlx: str = "payments.dlx"

    # Consumer settings
    consumer_prefetch_count: int = 10
    max_retry_attempts: int = 3

    # ── Payment gateway emulation ─────────────────────────────────────────────
    gateway_min_delay: float = 2.0
    gateway_max_delay: float = 5.0
    gateway_success_rate: float = 0.90  # 90% success probability

    # ── Webhook ───────────────────────────────────────────────────────────────
    webhook_timeout: float = 5.0
    webhook_max_retries: int = 3

    # ── Outbox poller ─────────────────────────────────────────────────────────
    outbox_poll_interval: float = 1.0  # seconds between polling cycles

    @field_validator("gateway_success_rate")
    @classmethod
    def validate_success_rate(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("gateway_success_rate must be between 0 and 1")
        return v


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton.

    Using lru_cache ensures we read & parse the environment once,
    and every module that calls get_settings() gets the same object.
    """
    return Settings()  # type: ignore[call-arg]
