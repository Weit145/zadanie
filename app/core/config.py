from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    database_url: str = Field(
        "postgresql+asyncpg://postgres:postgres@db:5432/postgres",
        validation_alias="DATABASE_URL",
    )
    telegram_bot_token: str | None = Field(None, validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_poll_timeout: int = Field(30, validation_alias="TELEGRAM_POLL_TIMEOUT")
    log_level: str = "INFO"


settings = Settings()
