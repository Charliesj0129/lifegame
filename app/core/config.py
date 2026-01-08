from pydantic import Field, AliasChoices, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any, Dict, List, Optional, Union


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
    SQLALCHEMY_DATABASE_URI: Optional[Union[PostgresDsn, str]] = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info) -> Any:
        if isinstance(v, str):
            return v
        # If any Postgres vars are missing, we might default to SQLite if intended, 
        # but for now let's just avoid crashing if they are missing and URI is not set.
        data = info.data if hasattr(info, 'data') else {}
        if not data.get("POSTGRES_SERVER"):
            return "sqlite+aiosqlite:///./data/game.db"
            
        return f"postgresql+asyncpg://{data.get('POSTGRES_USER')}:{data.get('POSTGRES_PASSWORD')}@{data.get('POSTGRES_SERVER')}:{data.get('POSTGRES_PORT')}/{data.get('POSTGRES_DB') or ''}"
    
    # Kuzu Graph DB
    KUZU_DATABASE_PATH: str = "./data/lifegame_graph"
    
    # Vector Memory (Chroma)
    CHROMA_DB_PATH: str = "./data/chroma_db"

    # Security
    SECRET_KEY: str = "default-insecure-key"

    # Home Assistant
    HA_WEBHOOK_SECRET: Optional[str] = None

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
