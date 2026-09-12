from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Every value comes from the environment or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    database_url: str
    embedding_backend: Literal["fake", "sentence_transformers"] = "fake"
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    geoadmin_base_url: str = "https://api3.geo.admin.ch"
    geoadmin_timeout_seconds: float = 5.0

    llm_backend: Literal["fake", "anthropic"] = "fake"
    llm_model: str = "claude-sonnet-5"
    anthropic_api_key: str | None = None
    crawl_max_pages: int = 200
    crawl_delay_seconds: float = 0.5
    fetch_timeout_seconds: float = 20.0
    fetch_retry_attempts: int = 3
    fetch_retry_backoff_seconds: float = 0.5
    user_agent: str = "swiss-grounding/0.1 (+https://github.com/thedionysus/swisscom-hackathon)"

    @model_validator(mode="after")
    def _anthropic_needs_key(self) -> "Settings":
        if self.llm_backend == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_BACKEND=anthropic")
        return self


def load_settings() -> Settings:
    return Settings()
