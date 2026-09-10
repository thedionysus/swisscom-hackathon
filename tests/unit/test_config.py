from swiss_grounding.config import Settings


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:1/db")
    monkeypatch.setenv("EMBEDDING_BACKEND", "fake")
    monkeypatch.setenv("EMBEDDING_DIM", "8")
    s = Settings()
    assert s.database_url == "postgresql://u:p@h:1/db"
    assert s.embedding_backend == "fake"
    assert s.embedding_dim == 8


def test_settings_rejects_unknown_backend(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:1/db")
    monkeypatch.setenv("EMBEDDING_BACKEND", "magic")
    import pytest

    with pytest.raises(ValueError):
        Settings()
