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
# Until the logistic model is fitted (Task 22), relevance blends the reranker with the retrieval rank:
# on the encoded corpus the reranker alone demoted the right Vaud passage (0.29) below wrong pages
# (0.45) that bge-m3 retrieval ranked lower (docs/RESEARCH.md §H3). A passage the reranker scores
# below RERANK_GATE keeps its reranker score, so a question with nothing relevant (Konstanz: ~0.00)
# still ends below the threshold.
PROVISIONAL_THRESHOLD = 0.20
RERANK_GATE = 0.20
RERANK_WEIGHT = 0.5
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
        if rerank_score < RERANK_GATE:
            return rerank_score
        retrieval = features[FEATURES.index("rrf_reciprocal")]
        return RERANK_WEIGHT * rerank_score + (1 - RERANK_WEIGHT) * retrieval


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
