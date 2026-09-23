"""Retrieval and status metrics with the pass thresholds of ADR 0016. Pure functions."""
import math
from collections.abc import Mapping, Sequence

THRESHOLDS: dict[str, float] = {"status_accuracy": 0.9, "recall@5": 0.8, "precision@5": 0.7, "ndcg@5": 0.7,
                                "faithfulness": 0.9}


def recall_at_k(ranked_keys: Sequence[str], expected: Sequence[str], k: int) -> float:
    """Share of expected-source fragments that some top-k citation key contains."""
    if not expected:
        return 1.0
    top = ranked_keys[:k]
    return sum(1 for frag in expected if any(frag in key for key in top)) / len(expected)


def precision_at_k(labels: Sequence[bool | None], k: int) -> float | None:
    judged = [x for x in labels[:k] if x is not None]
    return sum(judged) / len(judged) if judged else None


def ndcg_at_k(labels: Sequence[bool | None], k: int) -> float | None:
    gains = [1.0 if x else 0.0 for x in labels[:k]]
    positives = sum(1 for x in labels if x)
    if positives == 0:
        return None
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
    ideal = sum(1 / math.log2(i + 2) for i in range(min(positives, k)))
    return dcg / ideal


def mean(values: Sequence[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def passes(summary: Mapping[str, float | None]) -> dict[str, bool]:
    return {name: value is not None and value >= THRESHOLDS[name]
            for name, value in summary.items() if name in THRESHOLDS}
