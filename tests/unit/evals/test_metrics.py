import math

from swiss_grounding.evals.metrics import THRESHOLDS, ndcg_at_k, passes, precision_at_k, recall_at_k


def test_recall_is_the_share_of_expected_sources_in_the_top_k():
    ranked = ["https://a", "https://b#x", "https://c"]
    assert recall_at_k(ranked, ["b#x", "zzz"], k=2) == 0.5


def test_precision_counts_only_judged_items():
    assert precision_at_k([True, None, False, True, None, True], k=5) == 2 / 3


def test_precision_of_nothing_judged_is_none():
    assert precision_at_k([None, None], k=5) is None


def test_ndcg_binary():
    assert ndcg_at_k([True, False, True], k=5) == (1 + 1 / math.log2(4)) / (1 + 1 / math.log2(3))


def test_passes_against_thresholds():
    ok = {"status_accuracy": 0.95, "recall@5": 0.85, "precision@5": 0.75, "ndcg@5": 0.72}
    assert passes(ok) == {name: True for name in ok}
    assert passes({**ok, "recall@5": 0.5})["recall@5"] is False
    assert set(THRESHOLDS) >= set(ok)
