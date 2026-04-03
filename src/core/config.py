from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    api_key: str = Field(default="change-me", alias="API_KEY")

    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="payments", alias="POSTGRES_DB")
    postgres_user: str = Field(default="payments", alias="POSTGRES_USER")
    postgres_password: str = Field(default="payments", alias="POSTGRES_PASSWORD")

    database_url: str = Field(
        default="postgresql+asyncpg://payments:payments@postgres:5432/payments",
        alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg://payments:payments@postgres:5432/payments",
        alias="DATABASE_URL_SYNC",
    )

    rabbitmq_host: str = Field(default="rabbitmq", alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, alias="RABBITMQ_PORT")
    rabbitmq_user: str = Field(default="guest", alias="RABBITMQ_USER")
    rabbitmq_password: str = Field(default="guest", alias="RABBITMQ_PASSWORD")
    rabbitmq_url: str = Field(default="amqp://guest:guest@rabbitmq:5672/", alias="RABBITMQ_URL")

    outbox_poll_interval: int = Field(default=2, alias="OUTBOX_POLL_INTERVAL")
    outbox_batch_size: int = Field(default=50, alias="OUTBOX_BATCH_SIZE")
    outbox_max_retries: int = Field(default=5, alias="OUTBOX_MAX_RETRIES")

    webhook_timeout_seconds: int = Field(default=5, alias="WEBHOOK_TIMEOUT_SECONDS")
    webhook_max_retries: int = Field(default=3, alias="WEBHOOK_MAX_RETRIES")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    payments_exchange: str = Field(default="payments.exchange", alias="PAYMENTS_EXCHANGE")
    payments_queue: str = Field(default="payments.new", alias="PAYMENTS_QUEUE")
    payments_routing_key: str = Field(default="payments.new", alias="PAYMENTS_ROUTING_KEY")
    payments_dlx: str = Field(default="payments.dlx", alias="PAYMENTS_DLX")
    payments_dlq: str = Field(default="payments.dlq", alias="PAYMENTS_DLQ")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
