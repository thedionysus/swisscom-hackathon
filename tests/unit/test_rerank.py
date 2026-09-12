from dataclasses import replace
from datetime import UTC, date, datetime

from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.models import ChunkRecord, Hit
from swiss_grounding.retrieval.rerank import RerankWeights, rerank


def make_hit(chunk_id, extent_id, authority, categories, rrf=0.01):
    chunk = ChunkRecord(
        chunk_id=chunk_id, document_id=chunk_id, ordinal=0, text_original="o", text_en="e",
        heading_path="", anchor=None, extent_id=extent_id, authority=authority,
        categories=tuple(categories), url="https://x", identifier=None, title_original="t",
        title_en="t", language="de", valid_from=None, retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        license=None, source_id="s",
    )
    return Hit(chunk=chunk, rrf_score=rrf, dense_rank=1, lexical_rank=1)


TREE = LocationTree.from_locations(seed_locations())
QUERY_NODE = "CH-ZH-261-K3"


def test_more_specific_extent_ranks_higher_all_else_equal():
    hits = (
        make_hit(1, "CH", Authority.OFFICIAL_INFO, ["dogs"]),
        make_hit(2, "CH-ZH-261-K3", Authority.OFFICIAL_INFO, ["dogs"]),
        make_hit(3, "CH-ZH", Authority.OFFICIAL_INFO, ["dogs"]),
    )
    ranked = rerank(hits, TREE, QUERY_NODE, query_categories=("dogs",), weights=RerankWeights())
    assert [s.hit.chunk.chunk_id for s in ranked] == [2, 3, 1]


def test_category_overlap_boosts():
    hits = (
        make_hit(1, "CH", Authority.OFFICIAL_INFO, ["waste"]),
        make_hit(2, "CH", Authority.OFFICIAL_INFO, ["dogs", "hiking"]),
    )
    ranked = rerank(hits, TREE, QUERY_NODE, query_categories=("dogs",), weights=RerankWeights())
    assert ranked[0].hit.chunk.chunk_id == 2
    assert ranked[0].category_overlap == 1.0
    assert ranked[1].category_overlap == 0.0


def test_authority_breaks_ties():
    hits = (
        make_hit(1, "CH", Authority.INSTITUTIONAL, ["dogs"]),
        make_hit(2, "CH", Authority.FEDERAL_LAW, ["dogs"]),
    )
    ranked = rerank(hits, TREE, QUERY_NODE, query_categories=(), weights=RerankWeights())
    assert ranked[0].hit.chunk.chunk_id == 2


def test_specificity_values():
    hits = (make_hit(1, "CH-ZH-261-K3", Authority.OFFICIAL_INFO, []),
            make_hit(2, "CH", Authority.OFFICIAL_INFO, []))
    ranked = {s.hit.chunk.chunk_id: s for s in rerank(hits, TREE, QUERY_NODE, (), RerankWeights())}
    assert ranked[1].specificity == 1.0
    assert ranked[2].specificity == 0.25


def test_weights_zero_specificity_leaves_rrf_order():
    hits = (
        make_hit(1, "CH", Authority.OFFICIAL_INFO, [], rrf=0.05),
        make_hit(2, "CH-ZH-261-K3", Authority.OFFICIAL_INFO, [], rrf=0.01),
    )
    w = RerankWeights(specificity=0.0, category=0.0, authority=0.0, rrf=1.0)
    ranked = rerank(hits, TREE, QUERY_NODE, (), w)
    assert ranked[0].hit.chunk.chunk_id == 1


def make_event_hit(chunk_id, event_date):
    hit = make_hit(chunk_id, "CH-ZH-261-K3", Authority.OFFICIAL_INFO, ["waste"])
    return replace(hit, chunk=replace(hit.chunk, event_date=event_date))


def test_past_event_ranks_below_upcoming_event_all_else_equal():
    hits = (
        make_event_hit(1, date(2026, 1, 22)),     # already happened
        make_event_hit(2, date(2026, 9, 17)),     # upcoming
        make_event_hit(3, date(2026, 9, 12)),     # today: not past
        make_event_hit(4, None),                  # not an event
    )
    ranked = rerank(hits, TREE, QUERY_NODE, ("waste",), RerankWeights(), today=lambda: date(2026, 9, 12))
    ids = [s.hit.chunk.chunk_id for s in ranked]
    assert ids[-1] == 1                                        # penalised, not dropped
    assert ranked[0].score == ranked[1].score == ranked[2].score
    assert ranked[-1].score < ranked[0].score
