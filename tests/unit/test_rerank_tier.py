"""Tier ordering and the relevance floor (Task 9, decision D1).

`rerank` orders by `(tier, -score)`. The tier is the integer hop count from the
question's node up to the chunk's extent -- 0 is the question's own node, rising to the
federal root -- and a chunk only *claims* one when the cosine distance it was retrieved
at clears `RerankWeights.relevance_floor`.

Two invariants these tests exist to pin down:

- The floor decides **position, never membership**. A chunk below it keeps its place in
  the result, ordered by score among the other chunks that claimed no tier, so the floor
  can never turn a result into a false `no_evidence`.
- The tier is a *hard* outer key. A weak local chunk must not leapfrog a strong federal
  one on score, which is exactly what the pre-Task-9 `-score` ordering allowed.

Each ordering test is built so score alone would give the opposite answer, otherwise it
would be asserting the fixture rather than the behaviour.
"""
from datetime import UTC, datetime

from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.models import ChunkRecord, Hit
from swiss_grounding.retrieval.rerank import RerankWeights, rerank

TREE = LocationTree.from_locations(seed_locations())
# The question is asked about the commune, so a commune chunk is tier 0 and a federal
# chunk is tier 2 (commune -> canton -> country).
QUERY_NODE = "CH-ZH-261"
FLOOR = 0.55
WEIGHTS = RerankWeights(relevance_floor=FLOOR)


def make_hit(chunk_id: int, extent_id: str, distance: float | None, rrf: float = 0.01) -> Hit:
    chunk = ChunkRecord(
        chunk_id=chunk_id, document_id=chunk_id, ordinal=0, text_original="o", text_en="e",
        heading_path="", anchor=None, extent_id=extent_id,
        authority=Authority.OFFICIAL_INFO, categories=(), url="https://x", identifier=None,
        title_original="t", title_en="t", language="de", valid_from=None,
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC), license=None, source_id="s",
    )
    return Hit(chunk=chunk, rrf_score=rrf, dense_rank=1, lexical_rank=1, distance=distance)


def federal(distance: float | None, chunk_id: int = 1, rrf: float = 0.05) -> Hit:
    """A federal chunk given a large rrf, so it wins on score alone and can only lose on tier."""
    return make_hit(chunk_id, "CH", distance, rrf=rrf)


def municipal(distance: float | None, chunk_id: int = 2, rrf: float = 0.01) -> Hit:
    return make_hit(chunk_id, "CH-ZH-261", distance, rrf=rrf)


def ranked_extents(hits: tuple[Hit, ...]) -> list[str]:
    return [s.hit.chunk.extent_id for s in rerank(hits, TREE, QUERY_NODE, (), WEIGHTS)]


def test_score_alone_would_put_the_federal_chunk_first():
    """The premise of every ordering test below: without the tier, rrf carries the federal
    chunk to the top. If this ever stops holding, the other tests stop proving anything."""
    scored = rerank((federal(0.40), municipal(0.48)), TREE, QUERY_NODE, (), WEIGHTS)
    by_extent = {s.hit.chunk.extent_id: s.score for s in scored}
    assert by_extent["CH"] > by_extent["CH-ZH-261"]


def test_local_evidence_leads_when_it_clears_the_floor():
    ranked = rerank((federal(0.40), municipal(0.48)), TREE, QUERY_NODE, (), WEIGHTS)
    assert ranked[0].hit.chunk.extent_id == "CH-ZH-261"
    assert ranked[0].tier == 0
    assert ranked[1].tier == 2


def test_a_weak_local_chunk_does_not_leapfrog_but_is_still_returned():
    ranked = rerank((federal(0.40), municipal(0.72)), TREE, QUERY_NODE, (), WEIGHTS)
    assert ranked[0].hit.chunk.extent_id == "CH"
    assert any(s.hit.chunk.extent_id == "CH-ZH-261" for s in ranked)   # not excluded
    assert ranked[1].tier is None                                      # claimed no tier


def test_the_floor_removes_nothing_at_all():
    """Every hit survives however far above the floor it sits; the floor moves chunks, it
    does not drop them, so it can never manufacture a `no_evidence`."""
    hits = (federal(1.90), municipal(1.95), make_hit(3, "CH-ZH", 1.99))
    assert len(rerank(hits, TREE, QUERY_NODE, (), WEIGHTS)) == 3
    assert {s.tier for s in rerank(hits, TREE, QUERY_NODE, (), WEIGHTS)} == {None}


def test_a_chunk_exactly_at_the_floor_still_claims_its_tier():
    """The floor is inclusive: at the floor is not below it."""
    ranked = rerank((federal(0.40), municipal(FLOOR)), TREE, QUERY_NODE, (), WEIGHTS)
    assert ranked[0].hit.chunk.extent_id == "CH-ZH-261"
    assert ranked[0].tier == 0


def test_tiers_are_the_hop_count_up_the_tree():
    hits = (make_hit(1, "CH", 0.1), make_hit(2, "CH-ZH", 0.1), make_hit(3, "CH-ZH-261", 0.1))
    tiers = {s.hit.chunk.chunk_id: s.tier for s in rerank(hits, TREE, QUERY_NODE, (), WEIGHTS)}
    assert tiers == {1: 2, 2: 1, 3: 0}


def test_within_one_tier_the_higher_score_leads():
    """The tier is the outer key only; score still orders chunks that share a tier."""
    hits = (make_hit(1, "CH-ZH-261", 0.10, rrf=0.01), make_hit(2, "CH-ZH-261", 0.50, rrf=0.09))
    ranked = rerank(hits, TREE, QUERY_NODE, (), WEIGHTS)
    assert [s.hit.chunk.chunk_id for s in ranked] == [2, 1]
    assert ranked[0].tier == ranked[1].tier == 0


def test_chunks_that_claimed_no_tier_are_ordered_by_score_among_themselves():
    hits = (make_hit(1, "CH-ZH-261", 0.90, rrf=0.01), make_hit(2, "CH", 0.95, rrf=0.09))
    ranked = rerank(hits, TREE, QUERY_NODE, (), WEIGHTS)
    assert [s.hit.chunk.chunk_id for s in ranked] == [2, 1]
    assert [s.tier for s in ranked] == [None, None]


def test_an_unmeasured_distance_claims_no_tier():
    """A lexical-only hit whose distance could not be filled in cannot be placed on the
    specificity ladder, so it ranks below everything that could -- but is still returned."""
    ranked = rerank((federal(0.40), municipal(None)), TREE, QUERY_NODE, (), WEIGHTS)
    assert [s.hit.chunk.extent_id for s in ranked] == ["CH", "CH-ZH-261"]
    assert ranked[1].tier is None


def test_an_extent_off_the_question_path_claims_no_tier_and_is_not_dropped():
    """The extent filter in `search.FILTER` means this should never reach the reranker.
    If it ever does, it must not be able to claim specificity it does not have."""
    hits = (federal(0.40), make_hit(9, "CH-BS", 0.10))
    ranked = rerank(hits, TREE, QUERY_NODE, (), WEIGHTS)
    assert [s.hit.chunk.extent_id for s in ranked] == ["CH", "CH-BS"]
    assert ranked[1].tier is None


def test_ordering_is_deterministic_when_tier_and_score_tie():
    """Two indistinguishable chunks must come back in the same order every run, because
    the recorded probes compare against a fixed citation order."""
    hits = (make_hit(7, "CH-ZH-261", 0.20), make_hit(3, "CH-ZH-261", 0.20))
    ranked = rerank(hits, TREE, QUERY_NODE, (), WEIGHTS)
    assert [s.hit.chunk.chunk_id for s in ranked] == [3, 7]
    assert ranked[0].score == ranked[1].score


def test_the_floor_ships_uncalibrated_but_present():
    """`RerankWeights()` carries a floor without anyone passing one; the value itself is
    a documented default, not a measured one (Task 9 Step 3)."""
    assert RerankWeights().relevance_floor == 0.55


def test_the_specificity_term_is_the_tier_decayed():
    """Both come from one tree walk (`hops_to_extent`), and this is the relationship that
    walk exists to make unbreakable: the tier is the hop count, the score's specificity
    term is that same hop count decayed. Deriving them separately let them drift."""
    hits = (make_hit(1, "CH", 0.1), make_hit(2, "CH-ZH", 0.1), make_hit(3, "CH-ZH-261", 0.1))
    ranked = rerank(hits, TREE, QUERY_NODE, (), WEIGHTS)
    assert all(s.tier is not None for s in ranked)
    for s in ranked:
        assert s.specificity == 1.0 / (1.0 + s.tier)


def test_a_demoted_chunk_keeps_the_specificity_its_extent_earns():
    """The floor withholds the *tier*; it does not also shrink the score's specificity
    term. The chunk is as local as it is either way, and docking it twice would count one
    decision against it in both ordering keys."""
    ranked = rerank((municipal(0.72),), TREE, QUERY_NODE, (), WEIGHTS)
    assert ranked[0].tier is None
    assert ranked[0].specificity == 1.0          # CH-ZH-261 is the question's own node
