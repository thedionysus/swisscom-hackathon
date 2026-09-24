from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.models import AUTHORITY_RANK
from swiss_grounding.retrieval.models import Hit, ScoredHit

# Events that already happened stay retrievable but should not outrank upcoming ones.
PAST_EVENT_PENALTY = 0.5
# Boost for an event happening today, decaying with days ahead so the nearest future
# event outranks later ones.
NEARNESS_BONUS = 0.5
NEARNESS_HALF_LIFE_DAYS = 14.0

# The cosine distance at or below which a chunk may claim a specificity tier.
#
# UNCALIBRATED. This is a documented default, not a measured one, and it must not be
# fitted to the corpus as it stands: that corpus is 71% federal and entirely boilerplate
# below canton level, so any value tuned against it would encode the gap rather than the
# behaviour. The measurement to beat: on the Dietikon
# forest question a download link sat at distance 0.5115 and the page's only real forest
# sentence at 0.5257, so distance does not currently separate relevant from irrelevant at
# all. 0.55 sits just above that pair deliberately: on today's index it admits both, which
# is the honest outcome when the signal cannot tell them apart. Calibrate after the
# contextual backfill (`recontext`) makes distance mean something.
#
# Because it cannot yet be trusted, it governs *tier eligibility only*. Nothing in this
# codebase may exclude a chunk on distance.
RELEVANCE_FLOOR = 0.55


@dataclass(frozen=True)
class RerankWeights:
    """The reranker's tuning constants: the additive score weights, and the relevance
    floor that decides which chunks may claim a specificity tier. rrf is multiplied by
    rrf_scale so it lives on a similar scale to the other terms."""
    specificity: float = 0.5
    category: float = 0.3
    authority: float = 0.2
    rrf: float = 1.0
    rrf_scale: float = 30.0
    relevance_floor: float = RELEVANCE_FLOOR


def hops_to_extent(tree: LocationTree, query_node_id: str, chunk_extent_id: str) -> int | None:
    """Steps up the location tree from the question's node to the chunk's extent, or None
    when that extent is not on the question's path.

    One walk, feeding both specificity terms below. They are not two measurements of two
    things: the tier *is* this integer, and the score is this same integer decayed, so
    computing them from separate walks would let a relationship that has to hold drift
    apart silently.

    Named `hops` and not `distance` on purpose. `LocationTree.distance` counts steps up a
    tree; `Hit.distance` is a cosine distance in embedding space. Both reach the reranker,
    they are published side by side on every citation as `tier` and `distance`, and one
    word for both is how they get confused.
    """
    return tree.distance(query_node_id, chunk_extent_id)


def specificity_score(hops: int | None) -> float:
    """1.0 for an exact extent match, decaying with each level of generality.

    This is `hops_to_extent`'s integer smoothed into the additive score and nothing else;
    None, an extent off the question's path, scores 0.0.
    """
    if hops is None:
        return 0.0
    return 1.0 / (1.0 + hops)


def specificity_tier(hops: int | None, hit_distance: float | None, floor: float) -> int | None:
    """The specificity tier a chunk may claim, or None when it may claim none.

    The tier is `hops_to_extent`'s hop count, the integer `specificity_score`'s decay is
    derived from: 0 for the question's own node, rising a step per level of generality up
    to the federal root. It is the reranker's outer ordering key.

    Three distinct situations all yield None, and all three mean the same thing to the
    caller -- *this chunk earns no claim on specificity*:

    - `hit_distance` is above `floor`. Being near the question is what buys the right to
      outrank more general evidence; a weak local chunk has not bought it. The chunk is
      still returned, ordered by score among its peers (`rerank`): the floor decides
      position, never membership, so it can never produce a false `no_evidence`.
    - `hit_distance` is None. The distance was never measured, which is not the same as
      being far, so the honest answer is to claim nothing rather than to guess either way.
    - `hops` is None, the extent being off the question's path. The extent predicate in
      `search.FILTER` means this cannot happen in a real query; if a caller reaches here
      with an off-path chunk anyway, it must not be able to claim specificity it does not
      have. Ranking it last is the conservative reading and keeps the reranker out of the
      business of validating its own input -- raising here would turn one bad row into a
      failed query for every other row beside it.
    """
    if hit_distance is None or hit_distance > floor:
        return None
    return hops


def category_overlap(query_categories: Sequence[str], chunk_categories: Sequence[str]) -> float:
    if not query_categories:
        return 0.0
    matched = sum(1 for c in query_categories if c in chunk_categories)
    return matched / len(query_categories)


def event_recency_factor(event_date: date | None, today: date) -> float:
    """1.0 for non-events; past events halved; future events boosted the nearer they are."""
    if event_date is None:
        return 1.0
    days = (event_date - today).days
    if days < 0:
        return PAST_EVENT_PENALTY
    return 1.0 + NEARNESS_BONUS / (1.0 + days / NEARNESS_HALF_LIFE_DAYS)


def _order_key(scored: ScoredHit) -> tuple[int, int, float, int]:
    """`(claimed a tier?, tier, -score, chunk_id)` -- the published ordering.

    The tier is the outer key, so a chunk that claimed one always precedes a chunk that
    did not, and a nearer extent always precedes a more general one. Score orders within
    a tier only. `chunk_id` breaks a remaining tie so two otherwise indistinguishable
    chunks come back in the same order on every run: the recorded probes compare citation
    order, and a sort that reshuffles on hash order would make them flap.

    A tier of None cannot be compared against an int, so it is carried in the first
    element rather than substituted for a sentinel integer -- there is no hop count that
    means "no hop count", and inventing one would publish a number that is not a distance
    up the tree.
    """
    claimed = scored.tier is not None
    return (0 if claimed else 1, scored.tier if claimed else 0,
            -scored.score, scored.hit.chunk.chunk_id)


def rerank(
    hits: Sequence[Hit],
    tree: LocationTree,
    query_node_id: str,
    query_categories: Sequence[str],
    weights: RerankWeights,
    today: Callable[[], date] = date.today,
) -> tuple[ScoredHit, ...]:
    """Score every hit and order them `(tier, -score)`, most specific first.

    `score` stays the within-tier ordering key but is no longer published: it moves with
    the question's extent (the same chunk measured 1.1918 at `CH` and 0.8168 at `8003`,
    entirely on the specificity term), so it told a caller nothing it could act on. The
    tier and the raw distance replace it on `Citation`.

    Nothing here drops a hit. Every hit in, every hit out.
    """
    current = today()
    scored = []
    for hit in hits:
        hops = hops_to_extent(tree, query_node_id, hit.chunk.extent_id)
        spec = specificity_score(hops)
        cat = category_overlap(query_categories, hit.chunk.categories)
        auth = AUTHORITY_RANK[hit.chunk.authority]
        score = (
            weights.specificity * spec
            + weights.category * cat
            + weights.authority * auth
            + weights.rrf * weights.rrf_scale * hit.rrf_score
        ) * event_recency_factor(hit.chunk.event_date, current)
        tier = specificity_tier(hops, hit.distance, weights.relevance_floor)
        scored.append(ScoredHit(hit=hit, score=score, specificity=spec,
                                category_overlap=cat, authority_score=auth, tier=tier))
    return tuple(sorted(scored, key=_order_key))
