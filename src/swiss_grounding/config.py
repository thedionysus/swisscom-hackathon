from typing import Annotated, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEFAULT_CORPUS_INDEXES = ("bge-m3",)


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

    # Encoding track (corpus schema). Keys are needed only while ingesting (ADR 0006).
    openai_api_key: str | None = None
    corpus_llm_provider: Literal["openai", "anthropic", "fake"] = "fake"
    corpus_doc_model: str = "gpt-5-mini"
    corpus_chunk_model: str = "gpt-5-nano"
    corpus_ocr_model: str = "gpt-5-mini"
    corpus_anthropic_model: str = "claude-haiku-4-5-20251001"
    # Embedding indexes the pipeline builds (CORPUS_INDEXES, comma-separated). bge-m3 is local and free;
    # openai-3l is paid and needs OPENAI_API_KEY. `corpus embed`/`index`/`run` build exactly these.
    corpus_indexes: Annotated[tuple[str, ...], NoDecode] = DEFAULT_CORPUS_INDEXES
    corpus_budget_usd: float = 100.0
    corpus_ocr_budget_usd: float = 10.0
    # Estimated input tokens per Batch API file; raise them to the account's enqueued-token limit (runbook).
    corpus_chat_tokens_per_file: int = 2_000_000
    corpus_embed_tokens_per_file: int = 2_000_000
    # Workers for HNSW index builds. 0 = serial: parallel builds need more /dev/shm than Docker's 64 MB default.
    corpus_index_parallel_workers: int = 0
    respect_robots: bool = True
    # Browser-style prefix, the conventional honest-bot form: ch.ch serves a 404 shell to user
    # agents without one (A11). Used for every corpus HTTP client.
    corpus_user_agent: str = (
        "Mozilla/5.0 (compatible; swiss-grounding/0.2; +https://github.com/thedionysus/swisscom-hackathon)"
    )
    data_dir: str = "data"

    @field_validator("corpus_indexes", mode="before")
    @classmethod
    def _split_indexes(cls, value: object) -> object:
        """`bge-m3, openai-3l` -> ("bge-m3", "openai-3l"): blanks dropped, duplicates removed, order kept."""
        parts = value.split(",") if isinstance(value, str) else value
        if not isinstance(parts, (list, tuple)):
            return value
        return tuple(dict.fromkeys(str(p).strip() for p in parts if str(p).strip()))

    @model_validator(mode="after")
    def _indexes_are_known(self) -> "Settings":
        # Imported here: keeps config free of the provider module's heavy imports.
        from swiss_grounding.corpus.providers import INDEXES
        if not self.corpus_indexes:
            raise ValueError(f"CORPUS_INDEXES must name at least one of {sorted(INDEXES)}")
        unknown = [name for name in self.corpus_indexes if name not in INDEXES]
        if unknown:
            raise ValueError(f"CORPUS_INDEXES: unknown index {', '.join(unknown)}; known: {sorted(INDEXES)}")
        if "openai-3l" in self.corpus_indexes and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when CORPUS_INDEXES includes openai-3l")
        return self

    @model_validator(mode="after")
    def _anthropic_needs_key(self) -> "Settings":
        if self.llm_backend == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_BACKEND=anthropic")
        return self

    @model_validator(mode="after")
    def _corpus_provider_needs_key(self) -> "Settings":
        if self.corpus_llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when CORPUS_LLM_PROVIDER=openai")
        if self.corpus_llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when CORPUS_LLM_PROVIDER=anthropic")
        return self


def load_settings() -> Settings:
    return Settings()
