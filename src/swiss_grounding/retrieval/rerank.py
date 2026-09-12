from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.models import AUTHORITY_RANK
from swiss_grounding.retrieval.models import Hit, ScoredHit

# Events that already happened stay retrievable but should not outrank upcoming ones.
PAST_EVENT_PENALTY = 0.5


@dataclass(frozen=True)
class RerankWeights:
    """Additive weights. rrf is multiplied by rrf_scale so it lives on a similar scale."""
    specificity: float = 0.5
    category: float = 0.3
    authority: float = 0.2
    rrf: float = 1.0
    rrf_scale: float = 30.0


def specificity_score(tree: LocationTree, query_node_id: str, chunk_extent_id: str) -> float:
    """1.0 for an exact extent match, decaying with each level of generality."""
    distance = tree.distance(query_node_id, chunk_extent_id)
    if distance is None:
        return 0.0
    return 1.0 / (1.0 + distance)


def category_overlap(query_categories: Sequence[str], chunk_categories: Sequence[str]) -> float:
    if not query_categories:
        return 0.0
    matched = sum(1 for c in query_categories if c in chunk_categories)
    return matched / len(query_categories)


def event_recency_factor(event_date: date | None, today: date) -> float:
    """1.0 for non-events and events today or later; a penalty for events already in the past."""
    if event_date is None or event_date >= today:
        return 1.0
    return PAST_EVENT_PENALTY


def rerank(
    hits: Sequence[Hit],
    tree: LocationTree,
    query_node_id: str,
    query_categories: Sequence[str],
    weights: RerankWeights,
    today: Callable[[], date] = date.today,
) -> tuple[ScoredHit, ...]:
    current = today()
    scored = []
    for hit in hits:
        spec = specificity_score(tree, query_node_id, hit.chunk.extent_id)
        cat = category_overlap(query_categories, hit.chunk.categories)
        auth = AUTHORITY_RANK[hit.chunk.authority]
        score = (
            weights.specificity * spec
            + weights.category * cat
            + weights.authority * auth
            + weights.rrf * weights.rrf_scale * hit.rrf_score
        ) * event_recency_factor(hit.chunk.event_date, current)
        scored.append(ScoredHit(hit=hit, score=score, specificity=spec,
                                category_overlap=cat, authority_score=auth))
    return tuple(sorted(scored, key=lambda s: (-s.score, s.hit.chunk.chunk_id)))
