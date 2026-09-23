import pytest
import typer

from swiss_grounding.cli import corpus_commands as cc
from swiss_grounding.config import Settings

TEST_URL = "postgresql://u:p@localhost:5433/swiss_grounding_test_ab12"
REAL_URL = "postgresql://u:p@localhost:5433/swiss_grounding"


def _settings(**overrides) -> Settings:
    base = {"database_url": REAL_URL, "corpus_llm_provider": "fake", "embedding_backend": "fake"}
    return Settings(**{**base, **overrides})


def test_priced_model_is_the_anthropic_model_under_the_anthropic_fallback():
    anthropic = _settings(corpus_llm_provider="anthropic", anthropic_api_key="k")
    assert cc._priced_model(anthropic, "gpt-5-mini") == "claude-haiku-4-5-20251001"
    assert cc._priced_model(_settings(), "gpt-5-mini") == "gpt-5-mini"


def test_priced_model_fails_fast_without_a_price():
    unknown = _settings(corpus_llm_provider="anthropic", anthropic_api_key="k", corpus_anthropic_model="claude-x")
    with pytest.raises(typer.Exit) as exc:
        cc._priced_model(unknown, "gpt-5-mini")
    assert exc.value.exit_code == 2


def test_fake_writes_are_allowed_only_on_test_databases_or_when_asked():
    assert cc._fake_write_allowed(TEST_URL, allow_fake=False)
    assert cc._fake_write_allowed(REAL_URL, allow_fake=True)
    assert not cc._fake_write_allowed(REAL_URL, allow_fake=False)


def test_the_guard_refuses_fake_writes_to_a_real_database():
    with pytest.raises(typer.Exit) as exc:
        cc._guard_fake(_settings(), uses_fake=True, allow_fake=False, what="describe")
    assert exc.value.exit_code == 2
    cc._guard_fake(_settings(), uses_fake=False, allow_fake=False, what="describe")
    cc._guard_fake(_settings(database_url=TEST_URL), uses_fake=True, allow_fake=False, what="describe")
