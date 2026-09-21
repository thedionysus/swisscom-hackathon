from datetime import UTC, date, datetime

from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.diversify import diversify
from swiss_grounding.retrieval.models import ChunkRecord, Hit, ScoredHit


def scored(chunk_id, document_id, extent_id, score, specificity, identifier=None, event_date=None):
    chunk = ChunkRecord(
        chunk_id=chunk_id, document_id=document_id, ordinal=0, text_original="o", text_en="e",
        heading_path="", anchor=None, extent_id=extent_id, authority=Authority.OFFICIAL_INFO,
        categories=(), url="u", identifier=identifier, title_original="t", title_en="t",
        language="de", valid_from=None, retrieved_at=datetime(2026, 1, 1, tzinfo=UTC), license=None,
        source_id="s", event_date=event_date,
    )
    hit = Hit(chunk=chunk, rrf_score=0.0, dense_rank=None, lexical_rank=None)
    return ScoredHit(hit=hit, score=score, specificity=specificity, category_overlap=0, authority_score=0)


def test_caps_chunks_per_document():
    items = (
        scored(1, 100, "CH", 0.9, 0.25), scored(2, 100, "CH", 0.8, 0.25),
        scored(3, 100, "CH", 0.7, 0.25), scored(4, 200, "CH", 0.6, 0.25),
    )
    out = diversify(items, limit=3, per_document_cap=2)
    assert [s.hit.chunk.chunk_id for s in out] == [1, 2, 4]


def test_guarantees_most_specific_extent_present():
    items = (
        scored(1, 100, "CH", 0.9, 0.25), scored(2, 200, "CH", 0.8, 0.25),
        scored(3, 300, "CH-ZH-261-K3", 0.1, 1.0),
    )
    out = diversify(items, limit=2, per_document_cap=2)
    ids = [s.hit.chunk.chunk_id for s in out]
    assert 3 in ids and len(ids) == 2


def test_empty_input():
    assert diversify((), limit=5, per_document_cap=2) == ()


def test_force_insert_respects_per_document_cap():
    items = (
        scored(1, 100, "CH", 0.9, 0.25), scored(2, 100, "CH", 0.8, 0.25),
        scored(3, 200, "CH", 0.7, 0.25), scored(4, 100, "CH-ZH-261-K3", 0.1, 1.0),
    )
    out = diversify(items, limit=3, per_document_cap=2)
    ids = [s.hit.chunk.chunk_id for s in out]
    assert 4 in ids
    assert sum(1 for s in out if s.hit.chunk.document_id == 100) <= 2


def test_swap_displaces_a_same_document_item_when_that_document_is_at_cap():
    items = (
        scored(1, 100, "CH", 0.9, 0.25), scored(2, 100, "CH", 0.8, 0.25),
        scored(3, 100, "CH-ZH-261-K3", 0.1, 1.0),
    )
    out = diversify(items, limit=2, per_document_cap=2)
    assert [s.hit.chunk.chunk_id for s in out] == [1, 3]


def test_no_swap_possible_leaves_selection_unchanged():
    items = (
        scored(1, 100, "CH", 0.9, 0.25), scored(2, 200, "CH-ZH-261-K3", 0.1, 1.0),
    )
    assert diversify(items, limit=3, per_document_cap=0) == ()


def test_zero_limit_returns_empty():
    items = (scored(1, 100, "CH", 0.9, 0.25),)
    assert diversify(items, limit=0, per_document_cap=2) == ()


TODAY = date(2026, 9, 21)


def test_caps_chunks_per_series():
    items = (
        scored(1, 101, "CH", 0.9, 0.25, identifier="cardboard-2026-09-24", event_date=date(2026, 9, 24)),
        scored(2, 102, "CH", 0.8, 0.25, identifier="cardboard-2026-10-01", event_date=date(2026, 10, 1)),
        scored(3, 103, "CH", 0.7, 0.25, identifier="cardboard-2026-10-08", event_date=date(2026, 10, 8)),
        scored(4, 104, "CH", 0.6, 0.25, identifier="cardboard-2026-10-15", event_date=date(2026, 10, 15)),
        scored(5, 105, "CH", 0.5, 0.25, identifier="cardboard-2026-10-22", event_date=date(2026, 10, 22)),
        scored(6, 200, "CH", 0.4, 0.25),
        scored(7, 300, "CH", 0.3, 0.25),
    )
    out = diversify(items, limit=5, per_document_cap=2, today=TODAY)
    # Only three cardboard hits survive; the freed slots go to the lower-ranked non-calendar hits.
    assert [s.hit.chunk.chunk_id for s in out] == [1, 2, 3, 6, 7]


def test_caps_two_series_independently():
    items = (
        scored(1, 101, "CH", 0.9, 0.25, identifier="cardboard-2026-09-24", event_date=date(2026, 9, 24)),
        scored(2, 102, "CH", 0.85, 0.25, identifier="paper-2026-09-29", event_date=date(2026, 9, 29)),
        scored(3, 103, "CH", 0.8, 0.25, identifier="cardboard-2026-10-01", event_date=date(2026, 10, 1)),
        scored(4, 104, "CH", 0.75, 0.25, identifier="paper-2026-10-13", event_date=date(2026, 10, 13)),
        scored(5, 105, "CH", 0.7, 0.25, identifier="cardboard-2026-10-08", event_date=date(2026, 10, 8)),
        scored(6, 106, "CH", 0.65, 0.25, identifier="paper-2026-10-27", event_date=date(2026, 10, 27)),
        scored(7, 107, "CH", 0.6, 0.25, identifier="cardboard-2026-10-15", event_date=date(2026, 10, 15)),
        scored(8, 108, "CH", 0.55, 0.25, identifier="paper-2026-11-10", event_date=date(2026, 11, 10)),
    )
    out = diversify(items, limit=8, per_document_cap=2, today=TODAY)
    # Each of the two series is capped at three, independently of the other.
    assert [s.hit.chunk.chunk_id for s in out] == [1, 2, 3, 4, 5, 6]


def test_series_cap_ignores_chunks_without_event_date():
    items = tuple(
        scored(i, 100 + i, "CH", 1.0 - i * 0.01, 0.25, identifier="cardboard-2026-09-10")
        for i in range(1, 6)
    )
    out = diversify(items, limit=5, per_document_cap=5, today=TODAY)
    # No chunk here carries an event_date, so the series cap never binds however many
    # of them share the same identifier prefix.
    assert [s.hit.chunk.chunk_id for s in out] == [1, 2, 3, 4, 5]


def test_series_cap_exempts_past_events():
    items = (
        scored(1, 101, "CH", 0.9, 0.25, identifier="cardboard-2026-09-24", event_date=date(2026, 9, 24)),
        scored(2, 102, "CH", 0.8, 0.25, identifier="cardboard-2026-10-01", event_date=date(2026, 10, 1)),
        scored(3, 103, "CH", 0.7, 0.25, identifier="cardboard-2026-10-08", event_date=date(2026, 10, 8)),
        # Below the three-per-series cap for upcoming dates, but this one is in the past, so it
        # is never counted against the cap and still gets a slot: a past-tense question about a
        # collection date must be able to find it.
        scored(4, 104, "CH", 0.1, 0.25, identifier="cardboard-2026-09-10", event_date=date(2026, 9, 10)),
    )
    out = diversify(items, limit=4, per_document_cap=2, today=TODAY)
    assert [s.hit.chunk.chunk_id for s in out] == [1, 2, 3, 4]
