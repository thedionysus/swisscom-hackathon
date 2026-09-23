import json

import numpy as np

from swiss_grounding.evals.fit import choose_threshold, fit_model, write_model
from swiss_grounding.serving.relevance import FEATURES, LogisticRelevance, load_relevance


def test_threshold_is_the_lowest_probability_reaching_the_target_precision():
    probs = [0.9, 0.8, 0.7, 0.4, 0.3]
    labels = [True, True, False, True, False]
    assert choose_threshold(probs, labels, target_precision=0.75) == 0.4


def test_threshold_refuses_when_the_target_is_unreachable():
    import pytest
    with pytest.raises(ValueError, match="no threshold"):
        choose_threshold([0.9, 0.8], [False, False], target_precision=0.9)


def test_fit_separates_a_separable_feature():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(200, len(FEATURES)))
    y = x[:, 0] > 0
    weights, _bias = fit_model(x, y)
    assert weights[0] > 1.0


def test_written_model_loads_as_logistic(tmp_path):
    path = tmp_path / "m.json"
    write_model(path, weights=[0.1] * len(FEATURES), bias=-1.0, threshold=0.4, reranker="r",
                meta={"pairs": 10})
    assert isinstance(load_relevance(path, "r"), LogisticRelevance)
    assert json.loads(path.read_text())["meta"]["pairs"] == 10
