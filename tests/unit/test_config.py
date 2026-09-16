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
