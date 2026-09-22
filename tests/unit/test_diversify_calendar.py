"""CALENDAR_CAP bounds calendar evidence in aggregate, on top of the existing per-series cap.

Five series of upcoming collection dates (waste, organic, cardboard, mobile, paper) can each
fill PER_SERIES_CAP slots, so together they can fill an entire answer with nothing but dates --
see diversify.py's module docstring for the live corpus numbers behind this. These tests pin
that the aggregate ceiling holds regardless of how many series are in play, while a single
series still gets its nearest dates in order.
"""
from datetime import UTC, date, datetime, timedelta
from itertools import count

import pytest

from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.diversify import CALENDAR_CAP, diversify
from swiss_grounding.retrieval.models import ChunkRecord, Hit, ScoredHit

TODAY = date(2026, 9, 21)
_next_id = count(1)


@pytest.fixture
def today() -> date:
    return TODAY


def _scored(chunk_id: int, document_id: int, score: float, *, identifier: str | None = None,
            event_date: date | None = None) -> ScoredHit:
    chunk = ChunkRecord(
        chunk_id=chunk_id, document_id=document_id, ordinal=0, text_original="o", text_en="e",
        heading_path="", anchor=None, extent_id="CH", authority=Authority.OFFICIAL_INFO,
        categories=(), url="u", identifier=identifier, title_original="t", title_en="t",
        language="de", valid_from=None, retrieved_at=datetime(2026, 1, 1, tzinfo=UTC), license=None,
        source_id="s", event_date=event_date,
    )
    hit = Hit(chunk=chunk, rrf_score=0.0, dense_rank=None, lexical_rank=None)
    return ScoredHit(hit=hit, score=score, specificity=0.25, category_overlap=0, authority_score=0)


def scored_event(series: str, days_ahead: int) -> ScoredHit:
    """An upcoming hit in ``series``, ranked higher the nearer it is -- like the reranker's
    nearest-future-first ordering for calendar evidence."""
    chunk_id = next(_next_id)
    event_date = TODAY + timedelta(days=days_ahead)
    return _scored(
        chunk_id, document_id=chunk_id, score=0.9 - days_ahead * 0.01,
        identifier=f"{series}-{event_date.isoformat()}", event_date=event_date,
    )


def scored_chunk(score: float) -> ScoredHit:
    """A non-calendar prose hit: no event date, no series."""
    chunk_id = next(_next_id)
    return _scored(chunk_id, document_id=chunk_id, score=score)


def sort_by_score(items):
    return tuple(sorted(items, key=lambda s: s.score, reverse=True))


def test_calendar_evidence_cannot_fill_an_answer(today):
    """Five series of upcoming events must not crowd out non-calendar evidence."""
    events = [scored_event(series=s, days_ahead=d) for s in
              ("waste", "organic", "cardboard", "mobile", "paper") for d in (1, 8, 15)]
    prose = [scored_chunk(score=0.4) for _ in range(5)]
    chosen = diversify(sort_by_score(events + prose), limit=10, today=today)
    assert sum(1 for c in chosen if c.hit.chunk.event_date) <= CALENDAR_CAP
    assert any(c.hit.chunk.event_date is None for c in chosen)


def test_a_single_series_still_keeps_its_nearest_dates(today):
    events = [scored_event(series="cardboard", days_ahead=d) for d in (1, 8, 15, 22, 29)]
    chosen = diversify(events, limit=10, today=today)
    assert [c.hit.chunk.event_date for c in chosen] == sorted(c.hit.chunk.event_date for c in chosen)
