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


def test_configured_indexes_come_local_first():
    settings = _settings(corpus_indexes=("openai-3l", "bge-m3"), openai_api_key="sk-test")
    assert [spec.name for spec in cc._configured_indexes(settings)] == ["bge-m3", "openai-3l"]


def test_an_unconfigured_index_is_refused_with_the_configured_list():
    with pytest.raises(typer.Exit) as exc:
        cc._require_configured(_settings(), "openai-3l")
    assert exc.value.exit_code == 2
    cc._require_configured(_settings(), "bge-m3")


def test_describe_runs_batches_and_direct_calls_side_by_side_when_direct_workers_are_set(monkeypatch):
    from swiss_grounding.corpus.hybrid_runner import HybridRunner
    from swiss_grounding.corpus.runner import BatchRunner, SyncRunner
    monkeypatch.setattr(cc, "_openai_client", lambda settings: object())
    hybrid = _settings(corpus_llm_provider="openai", openai_api_key="k", corpus_direct_workers=12)
    batch_only = _settings(corpus_llm_provider="openai", openai_api_key="k", corpus_direct_workers=0)
    assert isinstance(cc._describe_runner(hybrid, sync=False), HybridRunner)
    assert isinstance(cc._describe_runner(batch_only, sync=False), BatchRunner)
    assert isinstance(cc._describe_runner(hybrid, sync=True), SyncRunner)


def test_side_by_side_describe_is_estimated_at_the_direct_call_price():
    """The cap must hold even if every task ends up on the dearer path."""
    hybrid = _settings(corpus_llm_provider="openai", openai_api_key="k", corpus_direct_workers=12)
    batch_only = _settings(corpus_llm_provider="openai", openai_api_key="k", corpus_direct_workers=0)
    assert cc._estimate_at_batch_price(hybrid, sync=False) is False
    assert cc._estimate_at_batch_price(batch_only, sync=False) is True


def test_direct_workers_are_off_by_default():
    assert Settings.model_fields["corpus_direct_workers"].default == 0


def test_priced_model_is_the_apertus_model_under_apertus():
    apertus = _settings(corpus_llm_provider="apertus", apertus_api_key="k")
    assert cc._priced_model(apertus, "gpt-5-nano") == "swiss-ai/Apertus-v1.5-70B"


def test_apertus_runs_direct_calls_not_batches():
    from swiss_grounding.corpus.providers import ApertusLLM
    apertus = _settings(corpus_llm_provider="apertus", apertus_api_key="k")
    assert not cc._uses_batch(apertus, sync=False)
    assert isinstance(cc._llm(apertus), ApertusLLM)


def test_apertus_client_retries_up_to_the_direct_call_limit(monkeypatch):
    captured = {}
    monkeypatch.setattr(cc, "apertus_llm", lambda settings, **kw: captured.update(kw) or object())
    apertus = _settings(corpus_llm_provider="apertus", apertus_api_key="k")
    cc._llm(apertus)
    assert captured["max_retries"] == cc.DIRECT_MAX_RETRIES


def test_check_manifest_probes_nothing_for_a_source_with_only_pdf_urls():
    import httpx

    from swiss_grounding.cli import corpus_source_commands as cs
    from swiss_grounding.corpus.manifest import SourceEntry

    entry = SourceEntry(id="gl", name="GL", publisher="GL", authority="official_info", level="cantonal",
                        extent_id="CH-GL", connector="html", tier=2, languages=("de",),
                        config={"allow_prefixes": ["https://www.gl.ch/"],
                                "pdf_urls": [{"url": "https://www.gl.ch/a.pdf"}]})
    http = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    assert cs._check_html(http, entry, respect_robots=True) == 0


def test_sync_workers_is_apertus_workers_under_apertus_and_sync_workers_otherwise():
    apertus = _settings(corpus_llm_provider="apertus", apertus_api_key="k", apertus_workers=5)
    openai = _settings(corpus_llm_provider="openai", openai_api_key="k")
    assert cc._sync_workers(apertus) == 5
    assert cc._sync_workers(openai) == openai.corpus_sync_workers
