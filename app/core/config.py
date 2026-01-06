from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Life Gamification Agent v21"
    VERSION: str = "0.21.0"
    API_V1_STR: str = "/api/v1"

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "changethis"
    POSTGRES_DB: str = "lifgame"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "SQLALCHEMY_DATABASE_URI"),
    )

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Line Bot
    LINE_CHANNEL_ACCESS_TOKEN: Optional[str] = None
    LINE_CHANNEL_SECRET: Optional[str] = None

    # Google Gemini
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # OpenRouter
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = "google/gemini-3-flash-preview"

    # App Settings
    APP_BASE_URL: str = (
        "https://app-lifgame-955ea735.azurewebsites.net"  # Default to Prod for now, override in .env
    )
    AUTO_MIGRATE: bool = False
    ENABLE_LATENCY_LOGS: bool = Field(
        default=False,
        validation_alias=AliasChoices("ENABLE_LATENCY_LOGS", "LOG_LATENCY_ENABLED"),
    )
    ENABLE_LOADING_ANIMATION: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "ENABLE_LOADING_ANIMATION", "SHOW_LOADING_ANIMATION"
        ),
    )
    ENABLE_SCHEDULER: bool = False
    SCHEDULER_INTERVAL_SECONDS: int = 60

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
