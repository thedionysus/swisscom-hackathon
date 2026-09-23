"""Fit the logistic relevance model (sigmoid, not isotonic: < 1,000 pairs; RESEARCH §H1)."""
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from swiss_grounding.serving.relevance import FEATURES

TARGET_PRECISION = 0.9
REGULARISATION_C = 1.0


def check_training_labels(y: Sequence[bool]) -> None:
    """Fail clearly, before sklearn does, when there is nothing usable to fit on."""
    if len(y) == 0:
        raise ValueError("no usable dev labels: run `eval label --confirm-spend` and `eval label-check` first")
    if len(set(y)) < 2:
        raise ValueError("dev labels contain only relevant or only irrelevant pairs")


def fit_model(x: np.ndarray, y: np.ndarray) -> tuple[list[float], float]:
    from sklearn.linear_model import LogisticRegression
    model = LogisticRegression(C=REGULARISATION_C, max_iter=1000).fit(x, y)
    return [float(w) for w in model.coef_[0]], float(model.intercept_[0])


def choose_threshold(probs: Sequence[float], labels: Sequence[bool], target_precision: float) -> float:
    """Lowest probability p such that the pairs scoring >= p reach the target precision."""
    if not probs:
        raise ValueError("no labelled pairs to choose a threshold from")
    order = sorted(zip(probs, labels, strict=True), key=lambda t: -t[0])
    best, hits = None, 0
    for i, (p, label) in enumerate(order, start=1):
        hits += label
        if hits / i >= target_precision:
            best = p
    if best is None:
        raise ValueError(f"no threshold reaches precision {target_precision}; label more pairs or fix ranking")
    return best


def out_of_fold_probabilities(x: np.ndarray, y: np.ndarray, folds: int = 5) -> np.ndarray:
    """Dev-set probabilities from models that did not see each pair: the threshold is chosen on these."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_predict
    model = LogisticRegression(C=REGULARISATION_C, max_iter=1000)
    return cross_val_predict(model, x, y, cv=folds, method="predict_proba")[:, 1]


def write_model(path: Path, *, weights: Sequence[float], bias: float, threshold: float, reranker: str,
                meta: Mapping) -> None:
    if len(weights) != len(FEATURES):
        raise ValueError(f"expected {len(FEATURES)} weights (one per feature), got {len(weights)}")
    path.write_text(json.dumps({"reranker": reranker, "features": list(FEATURES), "weights": list(weights),
                                "bias": bias, "threshold": threshold, "fitted_at": datetime.now(UTC).isoformat(),
                                "meta": dict(meta)}, indent=2), encoding="utf-8")
