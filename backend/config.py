"""
Application settings loaded from environment / .env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Anthropic
    anthropic_api_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # Agent tuning
    agent_model: str = "claude-sonnet-4-20250514"
    max_react_iterations: int = 3
    min_confidence: int = 65
    tool_cache_ttl: int = 900   # seconds


@lru_cache
def get_settings() -> Settings:
    return Settings()
