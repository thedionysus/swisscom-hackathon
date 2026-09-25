import pytest

from swiss_grounding.evals.stats import bootstrap_ci, hit_at_k, mrr_at_k, percentile, wilson


def test_hit_at_1_needs_the_first_key_to_match_some_fragment():
    assert hit_at_k(["https://a/x", "https://b"], ["b"], k=1) == 0.0
    assert hit_at_k(["https://a/x", "https://b"], ["a/x"], k=1) == 1.0


def test_mrr_is_the_reciprocal_rank_of_the_first_match():
    assert mrr_at_k(["u1", "u2", "u3"], ["u3", "zz"], k=5) == pytest.approx(1 / 3)
    assert mrr_at_k(["u1", "u2", "u3"], ["u3"], k=2) == 0.0
    assert mrr_at_k(["u1"], [], k=5) == 1.0


def test_wilson_interval():
    lo, hi = wilson(8, 10)
    assert lo == pytest.approx(0.490, abs=1e-3) and hi == pytest.approx(0.943, abs=1e-3)
    assert wilson(0, 0) == (0.0, 1.0)
    assert wilson(0, 5)[0] == 0.0


def test_bootstrap_is_deterministic_and_brackets_the_mean():
    values = [0.0, 0.5, 1.0, 1.0, 0.25, 0.75]
    ci = bootstrap_ci(values)
    assert ci == bootstrap_ci(values)
    assert ci[0] <= sum(values) / len(values) <= ci[1]
    assert bootstrap_ci([]) is None
    assert bootstrap_ci([0.4]) == (0.4, 0.4)


def test_percentile_interpolates():
    assert percentile([1, 2, 3, 4], 50) == 2.5
    assert percentile([5], 95) == 5
    assert percentile([], 50) is None
