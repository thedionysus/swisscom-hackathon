from swiss_grounding.config import Settings


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:1/db")
    monkeypatch.setenv("EMBEDDING_BACKEND", "fake")
    monkeypatch.setenv("EMBEDDING_DIM", "8")
    s = Settings(_env_file=None)
    assert s.database_url == "postgresql://u:p@h:1/db"
    assert s.embedding_backend == "fake"
    assert s.embedding_dim == 8


def test_settings_rejects_unknown_backend(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:1/db")
    monkeypatch.setenv("EMBEDDING_BACKEND", "magic")
    import pytest

    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_ingest_settings_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:1/db")
    s = Settings(_env_file=None)
    assert s.llm_backend == "fake"
    assert s.llm_model == "claude-sonnet-5"
    assert s.crawl_max_pages == 200
    assert s.crawl_delay_seconds == 0.5
    assert s.user_agent.startswith("swiss-grounding/")
    assert s.anthropic_api_key is None


def test_anthropic_backend_requires_key(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:1/db")
    monkeypatch.setenv("LLM_BACKEND", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import pytest

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        Settings(_env_file=None)


def test_corpus_settings_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    for key in (
        "OPENAI_API_KEY", "CORPUS_LLM_PROVIDER", "RESPECT_ROBOTS", "CORPUS_BUDGET_USD",
        "DATA_DIR", "CORPUS_OCR_BUDGET_USD", "CORPUS_DOC_MODEL", "CORPUS_CHUNK_MODEL", "CORPUS_OCR_MODEL",
        "CORPUS_USER_AGENT", "CORPUS_INDEX_PARALLEL_WORKERS",
    ):
        monkeypatch.delenv(key, raising=False)
    from swiss_grounding.config import Settings
    s = Settings(_env_file=None)
    assert s.corpus_llm_provider == "fake"
    assert s.corpus_doc_model == "gpt-5-mini"
    assert s.corpus_chunk_model == "gpt-5-nano"
    assert s.corpus_ocr_model == "gpt-5-mini"
    assert s.corpus_budget_usd == 100.0
    assert s.corpus_ocr_budget_usd == 10.0
    assert s.respect_robots is True
    assert s.data_dir == "data"
    # Parallel HNSW builds need more /dev/shm than Docker's 64 MB default; serial is safe everywhere.
    assert s.corpus_index_parallel_workers == 0
    # ch.ch serves a 404 shell to user agents without a browser-style prefix (A11).
    assert s.corpus_user_agent == ("Mozilla/5.0 (compatible; swiss-grounding/0.2; "
                                   "+https://github.com/thedionysus/swisscom-hackathon)")


def test_openai_provider_needs_a_key(monkeypatch):
    import pytest
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from swiss_grounding.config import Settings
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        Settings(_env_file=None, corpus_llm_provider="openai")


def _corpus_env(monkeypatch, indexes: str | None = None, openai_key: str | None = None):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:1/db")
    for name, value in (("CORPUS_INDEXES", indexes), ("OPENAI_API_KEY", openai_key)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


def test_corpus_indexes_default_to_the_local_index(monkeypatch):
    _corpus_env(monkeypatch)
    assert Settings(_env_file=None).corpus_indexes == ("bge-m3",)


def test_corpus_indexes_parse_a_comma_separated_list(monkeypatch):
    _corpus_env(monkeypatch, " bge-m3 , openai-3l,", openai_key="sk-test")
    assert Settings(_env_file=None).corpus_indexes == ("bge-m3", "openai-3l")


def test_corpus_indexes_reject_an_unknown_index(monkeypatch):
    import pytest

    _corpus_env(monkeypatch, "bge-m3,cohere-v3")
    with pytest.raises(ValueError, match="cohere-v3"):
        Settings(_env_file=None)


def test_corpus_indexes_reject_an_empty_list(monkeypatch):
    import pytest

    _corpus_env(monkeypatch, " , ")
    with pytest.raises(ValueError, match="CORPUS_INDEXES"):
        Settings(_env_file=None)


def test_the_openai_index_needs_an_openai_key(monkeypatch):
    import pytest

    _corpus_env(monkeypatch, "bge-m3,openai-3l")
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        Settings(_env_file=None)
