import pytest

from swiss_grounding.corpus.budget import cost_usd, estimate_tokens


def test_token_estimate_is_conservative():
    assert estimate_tokens("a" * 300) == 100


def test_batch_cost_and_sync_doubles_it():
    assert cost_usd("gpt-5-nano", 1_000_000, 1_000_000) == pytest.approx(0.225)
    assert cost_usd("gpt-5-nano", 1_000_000, 1_000_000, batch=False) == pytest.approx(0.45)
    assert cost_usd("text-embedding-3-large", 1_000_000, 0) == pytest.approx(0.065)


def test_unknown_model_is_refused():
    with pytest.raises(KeyError):
        cost_usd("gpt-99", 1, 1)
