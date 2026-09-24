from swiss_grounding.cli.corpus_commands import DIRECT_MAX_RETRIES, OPENAI_EMBED_MAX_TOKENS, _llm
from swiss_grounding.config import Settings
from swiss_grounding.corpus.embed import token_groups
from swiss_grounding.corpus.providers import OpenAIEmbeddings


def _settings(**overrides):
    return Settings(_env_file=None, database_url="postgresql://x/y", **overrides)


def test_a_plain_sync_run_retries_rate_limits_like_direct_calls():
    llm = _llm(_settings(corpus_llm_provider="openai", openai_api_key="test"))
    assert llm._client.max_retries == DIRECT_MAX_RETRIES > 2


def test_the_embeddings_client_takes_a_retry_budget():
    assert OpenAIEmbeddings(api_key="test")._client.max_retries == 2
    assert OpenAIEmbeddings(api_key="test", max_retries=DIRECT_MAX_RETRIES)._client.max_retries == DIRECT_MAX_RETRIES


def test_sync_workers_default_to_eight_and_follow_the_environment(monkeypatch):
    assert _settings().corpus_sync_workers == 8
    monkeypatch.setenv("CORPUS_SYNC_WORKERS", "3")
    assert _settings().corpus_sync_workers == 3


def test_a_sync_embeddings_request_stays_far_under_the_300k_token_limit():
    assert OPENAI_EMBED_MAX_TOKENS <= 100_000
    pages = [{"text": "x" * 9_000} for _ in range(100)]    # 3,000 estimated tokens each, like dense OCR pages
    assert all(len(group) * 3_000 <= OPENAI_EMBED_MAX_TOKENS for group in token_groups(pages, 2048, OPENAI_EMBED_MAX_TOKENS))
