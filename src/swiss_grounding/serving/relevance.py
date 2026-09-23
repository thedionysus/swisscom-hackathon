"""Relevance probability (ADR 0012): reranker score until fitted, then a logistic model."""
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from swiss_grounding.serving.models import GroupHit

FEATURES: tuple[str, ...] = (
    "rerank_logit", "same_language", "rrf_reciprocal", "corroboration", "corroboration_na",
    "independent", "tier", "tier_na", "is_law", "age_years",
)
# Set from the probes in docs/RESEARCH.md §H1 (irrelevant ≈ 0.00-0.02, relevant ≥ 0.8); Task 28 re-checks it.
PROVISIONAL_THRESHOLD = 0.10
EPS = 1e-6


def _logit(p: float) -> float:
    p = min(max(p, EPS), 1 - EPS)
    return math.log(p / (1 - p))


def _sigmoid(z: float) -> float:
    """1 / (1 + exp(-z)), computed so neither branch ever overflows."""
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def feature_vector(g: GroupHit, *, rerank_score: float, question_lang: str | None, tier: int | None,
                   today: date) -> tuple[float, ...]:
    rep = g.representative
    seen = rep.modified_at or rep.fetched_at.date()
    return (
        _logit(rerank_score),
        1.0 if rep.language == question_lang else 0.0,
        1.0 / rep.rrf_rank if rep.rrf_rank else 0.0,
        g.corroboration or 0.0,
        1.0 if g.corroboration is None else 0.0,
        1.0 if g.corroboration_basis == "independent" else 0.0,
        float(tier) if tier is not None else 0.0,
        1.0 if tier is None else 0.0,
        1.0 if rep.authority.endswith("_law") else 0.0,
        max(0.0, (today - seen).days / 365.25),
    )


@dataclass(frozen=True)
class ProvisionalRelevance:
    threshold: float
    fitted: bool = False

    def probability(self, features: Sequence[float], *, rerank_score: float) -> float:
        return rerank_score


@dataclass(frozen=True)
class LogisticRelevance:
    weights: tuple[float, ...]
    bias: float
    threshold: float
    reranker: str
    fitted: bool = True

    def probability(self, features: Sequence[float], *, rerank_score: float) -> float:
        z = self.bias + sum(w * x for w, x in zip(self.weights, features, strict=True))
        return _sigmoid(z)


Relevance = ProvisionalRelevance | LogisticRelevance


def load_relevance(path: Path | str, reranker: str) -> Relevance:
    path = Path(path)
    if not path.exists():
        return ProvisionalRelevance(PROVISIONAL_THRESHOLD)
    data = json.loads(path.read_text())
    if data.get("reranker") != reranker:
        return ProvisionalRelevance(PROVISIONAL_THRESHOLD)
    if tuple(data["features"]) != FEATURES:
        raise ValueError(f"{path}: features {data['features']} do not match {list(FEATURES)}; refit")
    for key in ("weights", "bias", "threshold"):
        if key not in data:
            raise ValueError(f"{path}: missing required key {key!r}")
    return LogisticRelevance(tuple(float(w) for w in data["weights"]), float(data["bias"]),
                             float(data["threshold"]), reranker)
