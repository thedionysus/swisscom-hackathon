"""Rank metrics and confidence intervals for the golden set. Pure, deterministic functions."""
import math
import random
from collections.abc import Sequence

Z95 = 1.959964
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20260925


def _matches(key: str, expected: Sequence[str]) -> bool:
    return any(frag in key for frag in expected)


def hit_at_k(ranked_keys: Sequence[str], expected: Sequence[str], k: int) -> float:
    """1.0 when some top-k key contains an expected-source fragment."""
    return 1.0 if any(_matches(key, expected) for key in ranked_keys[:k]) else 0.0


def mrr_at_k(ranked_keys: Sequence[str], expected: Sequence[str], k: int) -> float:
    """Reciprocal rank of the first top-k key matching any expected fragment; 1.0 when none is expected."""
    if not expected:
        return 1.0
    return next((1 / (i + 1) for i, key in enumerate(ranked_keys[:k]) if _matches(key, expected)), 0.0)


def wilson(successes: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for a proportion; the whole unit interval when n is 0."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def percentile(values: Sequence[float], q: float) -> float | None:
    """Linear-interpolated q-th percentile (0-100)."""
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def bootstrap_ci(values: Sequence[float], *, resamples: int = BOOTSTRAP_RESAMPLES,
                 seed: int = BOOTSTRAP_SEED) -> tuple[float, float] | None:
    """Percentile bootstrap 95% interval of the mean, seeded so reruns agree."""
    if not values:
        return None
    rng = random.Random(seed)
    n = len(values)
    means = [sum(rng.choices(values, k=n)) / n for _ in range(resamples)]
    lo, hi = percentile(means, 2.5), percentile(means, 97.5)
    return (lo, hi) if lo is not None and hi is not None else None
