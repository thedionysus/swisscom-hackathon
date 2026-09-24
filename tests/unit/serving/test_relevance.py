import json
from datetime import date

import pytest

from swiss_grounding.serving.groups import collapse
from swiss_grounding.serving.relevance import (
    FEATURES,
    PROVISIONAL_THRESHOLD,
    LogisticRelevance,
    ProvisionalRelevance,
    feature_vector,
    load_relevance,
)
from tests.unit.serving.test_groups import cand

TODAY = date(2026, 9, 24)


def test_feature_vector_has_one_value_per_feature():
    [g] = collapse([cand("de", 1), cand("fr", 2)], {("g", "a"): (cand("de"), cand("fr"))}, "de")
    x = feature_vector(g, rerank_score=0.9, question_lang="de", tier=0, today=TODAY)
    assert len(x) == len(FEATURES)
    named = dict(zip(FEATURES, x, strict=True))
    assert named["same_language"] == 1.0 and named["corroboration"] == 1.0 and named["tier"] == 0.0


def test_provisional_below_the_gate_is_the_reranker_score():
    model = ProvisionalRelevance(threshold=PROVISIONAL_THRESHOLD)
    assert model.probability((0.0,) * len(FEATURES), rerank_score=0.05) == 0.05


def test_logistic_model_applies_weights():
    model = LogisticRelevance(weights=(1.0,) + (0.0,) * (len(FEATURES) - 1), bias=0.0, threshold=0.5,
                              reranker="r")
    assert model.probability((0.0,) * len(FEATURES), rerank_score=0.3) == 0.5


def test_load_falls_back_to_provisional_when_file_missing(tmp_path):
    assert isinstance(load_relevance(tmp_path / "none.json", "r"), ProvisionalRelevance)


def test_load_ignores_a_model_fitted_for_another_reranker(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"reranker": "other", "features": list(FEATURES),
                                "weights": [0.0] * len(FEATURES), "bias": 0.0, "threshold": 0.4}))
    assert isinstance(load_relevance(path, "r"), ProvisionalRelevance)


def test_load_rejects_a_model_with_different_features(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"reranker": "r", "features": ["x"], "weights": [1.0], "bias": 0.0,
                                "threshold": 0.4}))
    with pytest.raises(ValueError, match="features"):
        load_relevance(path, "r")


def test_load_rejects_a_model_missing_a_required_key(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"reranker": "r", "features": list(FEATURES), "bias": 0.0, "threshold": 0.4}))
    with pytest.raises(ValueError, match=r"m\.json.*weights"):
        load_relevance(path, "r")


@pytest.mark.parametrize("z_weight", [1000.0, -1000.0])
def test_logistic_probability_is_stable_for_extreme_scores(z_weight):
    model = LogisticRelevance(weights=(z_weight,) + (0.0,) * (len(FEATURES) - 1), bias=0.0, threshold=0.5,
                              reranker="r")
    p = model.probability((1.0,) + (0.0,) * (len(FEATURES) - 1), rerank_score=0.5)
    assert 0.0 <= p <= 1.0
    assert (p > 0.999999) if z_weight > 0 else (p < 0.000001)


def _features(rrf_rank: int) -> tuple[float, ...]:
    x = [0.0] * len(FEATURES)
    x[FEATURES.index("rrf_reciprocal")] = 1.0 / rrf_rank
    return tuple(x)


def test_provisional_blends_reranker_with_retrieval_rank():
    model = ProvisionalRelevance(threshold=PROVISIONAL_THRESHOLD)
    top_retrieved = model.probability(_features(1), rerank_score=0.37)
    reranker_favourite = model.probability(_features(5), rerank_score=0.46)
    assert top_retrieved > reranker_favourite


def test_provisional_keeps_near_zero_reranker_scores_below_the_threshold():
    model = ProvisionalRelevance(threshold=PROVISIONAL_THRESHOLD)
    assert model.probability(_features(1), rerank_score=0.01) < PROVISIONAL_THRESHOLD
