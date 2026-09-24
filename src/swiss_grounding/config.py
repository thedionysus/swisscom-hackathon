from typing import Annotated, Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from swiss_grounding.serving.models import LANGS as SUPPORTED_LANGUAGES

DEFAULT_CORPUS_INDEXES = ("bge-m3",)
ZBERN_HOSTED_URL = "https://mcp.zbern.ch/mcp"
ZBERN_DEFAULT_EXCLUDE = ("query", "list_tables", "describe_table", "get_reference")
DEFAULT_TRANSLATE_QUERY_LANGUAGES = ("de", "fr", "it", "en")


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

    # Encoding track (corpus schema). Keys are needed only while ingesting.
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
    # Direct calls run beside the Batch API while describing (0 = batches only). Direct calls are limited
    # per minute, separately from the Batch queue, so both together roughly double throughput at low
    # usage tiers; they cost twice the batch price. Size to the account's tokens-per-minute limit.
    corpus_direct_workers: int = 0
    # Parallel requests of a plain --sync run (OCR, describe). Lower it on an account with a low tokens-per-minute
    # limit: 8 kept a 200k-TPM account at its ceiling.
    corpus_sync_workers: int = 8
    # Workers for HNSW index builds. 0 = serial: parallel builds need more /dev/shm than Docker's 64 MB default.
    corpus_index_parallel_workers: int = 0
    respect_robots: bool = True
    # Browser-style prefix, the conventional honest-bot form: ch.ch serves a 404 shell to user
    # agents without one. Used for every corpus HTTP client.
    corpus_user_agent: str = (
        "Mozilla/5.0 (compatible; swiss-grounding/0.2; +https://github.com/thedionysus/swisscom-hackathon)"
    )
    data_dir: str = "data"

    # Serving track. Keyless by default: bge-m3 embeds the question locally.
    # Deliberately separate from the legacy EMBEDDING_BACKEND (default "fake"): serving never uses
    # fake query vectors unless a test asks for them with QUERY_EMBEDDER=fake.
    serving_index: Literal["bge-m3", "openai-3l"] = "bge-m3"
    query_embedder: Literal["auto", "fake"] = "auto"
    # "auto" picks by hardware: bge-reranker-v2-m3 on MPS/CUDA, the small model on CPU.
    reranker_model: str = "auto"
    reranker_gpu_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_cpu_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    reranker_max_tokens: int = 512
    rerank_candidates: int = 30
    # On CPU the reranker is ~10x slower (docs/EVALUATION.md): fewer, shorter candidates.
    rerank_candidates_cpu: int = 20
    reranker_max_tokens_cpu: int = 256
    local_candidate_quota: int = 10
    hnsw_ef_search: int = 100
    relevance_model_path: str = "evals/relevance_model.json"
    # Translation. With SUPERTEXT_API_KEY set, the server translates the question into the
    # other language stores before searching and cited passages back into the question's language.
    # Without the key nothing is translated and the server behaves as before.
    supertext_api_key: str | None = None
    supertext_base_url: str = "https://api.supertext.com/v1"
    supertext_timeout_seconds: float = 8.0
    # Stores the question is translated into (TRANSLATE_QUERY_LANGUAGES, comma-separated); its own
    # language is always skipped. Romansh is off by default: measured 2026-09-24, the reranker scores
    # weak Romansh passages 0.95 against a Romansh query (0.00 against the German question), which
    # pushed the right German page out of the top five. The Romansh store is still searched by the
    # multilingual embedding, and a Romansh question is translated into the other four.
    translate_query_languages: Annotated[tuple[str, ...], NoDecode] = DEFAULT_TRANSLATE_QUERY_LANGUAGES
    translate_citations: bool = True
    transport_base_url: str = "https://transport.opendata.ch/v1"
    reference_rate_url: str = "https://www.bwo.admin.ch/de/referenzzinssatz"
    lookup_timeout_seconds: float = 8.0
    # The dump is a release asset of our private repository, downloaded with `gh`.
    dump_release_repo: str = "thedionysus/swisscom-hackathon"
    dump_release_tag: str = "corpus-latest"

    # Swiss Parliament tools from the hosted zbern.ch MCP server. On once ZBERN_MCP_TOKEN is present (`setup`
    # installs it from the private release); set ZBERN_MCP_URL empty to turn the tools off.
    zbern_mcp_url: str | None = ZBERN_HOSTED_URL
    zbern_mcp_token: SecretStr | None = None
    zbern_mcp_prefix: str = "zbern_"
    # zbern tool names (without the prefix) not to serve, comma-separated. The raw-SQL tools are off by
    # default: they add four calls a model may take before answering; set ZBERN_MCP_EXCLUDE= to serve them.
    zbern_mcp_exclude: Annotated[tuple[str, ...], NoDecode] = ZBERN_DEFAULT_EXCLUDE
    zbern_mcp_timeout_seconds: float = 60.0
    # How often the zbern tool list and instructions are re-read, so changes there show up without a restart.
    zbern_mcp_refresh_seconds: float = 300.0

    @field_validator("corpus_indexes", "translate_query_languages", "zbern_mcp_exclude", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
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
    def _translate_languages_are_known(self) -> "Settings":
        unknown = [lang for lang in self.translate_query_languages if lang not in SUPPORTED_LANGUAGES]
        if unknown:
            raise ValueError(f"TRANSLATE_QUERY_LANGUAGES: unknown language {', '.join(unknown)}; "
                             f"known: {', '.join(SUPPORTED_LANGUAGES)}")
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

    @model_validator(mode="after")
    def _openai_serving_needs_key(self) -> "Settings":
        if self.serving_index == "openai-3l" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when SERVING_INDEX=openai-3l")
        return self


def load_settings() -> Settings:
    return Settings()
