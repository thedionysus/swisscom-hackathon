from datetime import UTC, date, datetime

from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.cite import build_citation
from swiss_grounding.retrieval.models import ChunkRecord, Hit, ScoredHit


def test_citation_copies_fields_and_labels_extent():
    chunk = ChunkRecord(
        chunk_id=7, document_id=3, ordinal=0, text_original="Im Kanton Zürich gilt Leinenpflicht.",
        text_en="In the Canton of Zurich dogs must be leashed.", heading_path="Leinenpflicht",
        anchor="leinenpflicht", extent_id="CH-ZH", authority=Authority.OFFICIAL_INFO,
        categories=("dogs",), url="https://www.zh.ch/x", identifier=None,
        title_original="Hunde", title_en="Dogs", language="de", valid_from=date(2020, 1, 1),
        retrieved_at=datetime(2026, 9, 1, tzinfo=UTC), license="zh terms", source_id="zh_ch",
        event_date=date(2026, 9, 17),
    )
    sh = ScoredHit(
        hit=Hit(chunk=chunk, rrf_score=0.0, dense_rank=1, lexical_rank=None, distance=0.4321),
        score=0.7, specificity=0.5, category_overlap=1.0, authority_score=0.6, tier=1,
    )
    tree = LocationTree.from_locations(seed_locations())
    c = build_citation(sh, tree)
    assert c.url == "https://www.zh.ch/x" and c.anchor == "leinenpflicht"
    assert c.extent_label == "Zurich" and c.extent_id == "CH-ZH"
    assert c.authority == "official_info"
    assert c.snippet_original.startswith("Im Kanton")
    # `score` moved with the question's extent and told a caller
    # nothing it could act on, so the citation publishes the tier and the raw distance in
    # its place. Both are lower-is-better.
    assert c.tier == 1
    assert c.distance == 0.4321
    assert c.license == "zh terms"
    assert c.event_date == date(2026, 9, 17)


def _scored(distance: float | None, tier: int | None) -> ScoredHit:
    chunk = ChunkRecord(
        chunk_id=1, document_id=1, ordinal=0, text_original="o", text_en="e",
        heading_path="", anchor=None, extent_id="CH-ZH", authority=Authority.OFFICIAL_INFO,
        categories=(), url="https://x", identifier=None, title_original="t", title_en="t",
        language="de", valid_from=None, retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        license=None, source_id="s",
    )
    return ScoredHit(
        hit=Hit(chunk=chunk, rrf_score=0.0, dense_rank=1, lexical_rank=None, distance=distance),
        score=0.7, specificity=0.5, category_overlap=0.0, authority_score=0.6, tier=tier,
    )


def test_a_citation_no_longer_publishes_a_score():
    """The reranker still computes one -- it orders within a tier -- but it is not a number
    the caller can compare across calls, so it stops being published."""
    tree = LocationTree.from_locations(seed_locations())
    c = build_citation(_scored(0.5, 1), tree)
    assert not hasattr(c, "score")


def test_a_citation_carries_an_unclaimed_tier_and_an_unmeasured_distance_as_none():
    """None is a real outcome on both fields and must survive to the caller rather than be
    rounded into a number: `tier is None` means the chunk earned no specificity claim, and
    `distance is None` means nothing measured it -- not that it is far away."""
    tree = LocationTree.from_locations(seed_locations())
    c = build_citation(_scored(None, None), tree)
    assert c.tier is None
    assert c.distance is None


def test_the_published_distance_is_rounded_but_not_invented():
    tree = LocationTree.from_locations(seed_locations())
    assert build_citation(_scored(0.123456789, 0), tree).distance == 0.1235
