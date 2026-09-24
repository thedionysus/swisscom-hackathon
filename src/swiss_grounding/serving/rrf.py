"""Reciprocal rank fusion and the local-candidate quota."""
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


def select_with_pool(order: Sequence[Hashable], pool: Sequence[Hashable], *, n: int,
                     quota: int) -> list[Hashable]:
    """Up to `quota` items from `pool` (in its order), then the rest of the top `n` from `order`.

    Never more than `n` items: the quota is capped by `n`.
    """
    picked = list(dict.fromkeys(pool))[: max(0, min(quota, n))]
    taken = set(picked)
    rest = [k for k in order if k not in taken][: max(0, n - len(picked))]
    return picked + rest


def select_with_quota(order: Sequence[Hashable], *, is_local: Callable[[Hashable], bool],
                      n: int, quota: int) -> list[Hashable]:
    """The top `n` of `order`, guaranteeing up to `quota` local items, keeping `order`'s sequence."""
    keep = set(select_with_pool(order, [k for k in order if is_local(k)], n=n, quota=quota))
    return [k for k in order if k in keep]
