from os import getenv

from pydantic import AmqpDsn, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "payment-service"
    debug: bool = False
    api_key: SecretStr

    database_url: PostgresDsn
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    rabbitmq_url: AmqpDsn

    payments_exchange: str = "payments"
    payments_new_queue: str = "payments.new"

    base_backoff_sec: float = 1.0
    backoff_factor: float = 2.0
    max_retry_attempts: int = 3

    gateway_min_delay_sec: float = 2.0
    gateway_max_delay_sec: float = 5.0
    gateway_success_rate: float = 0.90

    webhook_timeout_sec: float = 5.0
    webhook_max_retries: int = 3
    webhook_base_backoff_sec: float = 1.0
    webhook_backoff_factor: float = 2.0

    outbox_poll_interval_sec: float = 1.0
    publish_batch_size: int = 100

    @field_validator("gateway_success_rate")
    @classmethod
    def validate_success_rate(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("gateway_success_rate must be between 0 and 1")
        return v


settings = Settings()  # type: ignore[call-arg]
