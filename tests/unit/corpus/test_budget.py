import pytest

from swiss_grounding.corpus.budget import cost_usd, estimate_tokens, tasks_that_fit


def test_token_estimate_is_conservative():
    assert estimate_tokens("a" * 300) == 100


def test_batch_cost_and_sync_doubles_it():
    assert cost_usd("gpt-5-nano", 1_000_000, 1_000_000) == pytest.approx(0.225)
    assert cost_usd("gpt-5-nano", 1_000_000, 1_000_000, batch=False) == pytest.approx(0.45)
    assert cost_usd("text-embedding-3-large", 1_000_000, 0) == pytest.approx(0.065)


def test_unknown_model_is_refused():
    with pytest.raises(KeyError):
        cost_usd("gpt-99", 1, 1)


def test_the_anthropic_fallback_model_has_a_price():
    from swiss_grounding.corpus.budget import PRICES
    assert PRICES["claude-haiku-4-5-20251001"] == PRICES["claude-haiku-4-5"] == (0.5, 2.5)
    assert cost_usd("claude-haiku-4-5", 1_000_000, 1_000_000, batch=False) == pytest.approx(6.0)


def test_tasks_that_fit_uses_the_average_price_per_task():
    # 3,400 tasks estimated at $9.80 total, but only $3.80 is left: ~1,318 tasks fit.
    assert tasks_that_fit(remaining_usd=3.80, estimate_usd=9.80, num_tasks=3_400) == 1_318


def test_tasks_that_fit_is_capped_at_num_tasks_and_never_negative():
    assert tasks_that_fit(remaining_usd=1_000.0, estimate_usd=1.0, num_tasks=5) == 5
    assert tasks_that_fit(remaining_usd=-1.0, estimate_usd=1.0, num_tasks=5) == 0
    assert tasks_that_fit(remaining_usd=1.0, estimate_usd=0.0, num_tasks=5) == 0
    assert tasks_that_fit(remaining_usd=1.0, estimate_usd=1.0, num_tasks=0) == 0
