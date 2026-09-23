import json

import numpy as np
import pytest

from swiss_grounding.evals.fit import (
    check_training_labels,
    choose_threshold,
    fit_model,
    write_model,
)
from swiss_grounding.serving.relevance import FEATURES, LogisticRelevance, load_relevance


def test_threshold_is_the_lowest_probability_reaching_the_target_precision():
    probs = [0.9, 0.8, 0.7, 0.4, 0.3]
    labels = [True, True, False, True, False]
    assert choose_threshold(probs, labels, target_precision=0.75) == 0.4


def test_threshold_refuses_when_the_target_is_unreachable():
    with pytest.raises(ValueError, match="no threshold"):
        choose_threshold([0.9, 0.8], [False, False], target_precision=0.9)


def test_check_training_labels_rejects_no_rows():
    with pytest.raises(ValueError, match="no usable dev labels"):
        check_training_labels([])


def test_check_training_labels_rejects_a_single_class():
    with pytest.raises(ValueError, match="only relevant or only irrelevant"):
        check_training_labels([True, True, True])


def test_check_training_labels_accepts_both_classes():
    check_training_labels([True, False])


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


def test_write_model_refuses_a_weight_vector_of_the_wrong_length(tmp_path):
    with pytest.raises(ValueError, match="expected .* weights"):
        write_model(tmp_path / "m.json", weights=[0.1] * (len(FEATURES) - 1), bias=-1.0, threshold=0.4,
                   reranker="r", meta={})
