"""Reciprocal rank fusion and the local-candidate quota (RESEARCH §H2)."""
from collections.abc import Callable, Hashable, Mapping, Sequence

RRF_K = 60


def fuse(lists: Mapping[str, Sequence[Hashable]]) -> list[tuple[Hashable, float, frozenset[str]]]:
    """(key, score, arms that found it), best first; ties keep first-seen order."""
    scores: dict[Hashable, float] = {}
    arms: dict[Hashable, set[str]] = {}
    for arm, keys in lists.items():
        for rank, key in enumerate(keys, start=1):
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank)
            arms.setdefault(key, set()).add(arm)
    order = sorted(scores, key=lambda k: -scores[k])
    return [(k, scores[k], frozenset(arms[k])) for k in order]


def select_with_quota(order: Sequence[Hashable], *, is_local: Callable[[Hashable], bool],
                      n: int, quota: int) -> list[Hashable]:
    """The top `n` of `order`, guaranteeing up to `quota` local items, keeping `order`'s sequence."""
    local = set([k for k in order if is_local(k)][:quota])
    rest = [k for k in order if k not in local][: max(0, n - len(local))]
    keep = local | set(rest)
    return [k for k in order if k in keep]
