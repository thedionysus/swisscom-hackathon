"""UPCOMING_CALENDAR_CAP bounds *upcoming* calendar evidence in aggregate, on top of the
existing per-series cap.

Five series of upcoming collection dates (waste, organic, cardboard, mobile, paper) can each
fill PER_SERIES_CAP slots, so together they can fill an entire answer with nothing but dates --
see diversify.py's module docstring for the live corpus numbers behind this, and for what this
cap deliberately leaves unbounded (past calendar evidence; an event-dated chunk with no
identifier). These tests pin that the aggregate ceiling holds regardless of how many series are
in play, that a single series still gets its nearest dates in order, and that both places the
ceiling is enforced -- the direct-append branch and the swap-in branch of ``diversify()`` --
actually enforce it rather than merely intending to.
"""
from datetime import UTC, date, datetime, timedelta
from itertools import count

import pytest

from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.diversify import UPCOMING_CALENDAR_CAP, _capped_series, diversify
from swiss_grounding.retrieval.models import ChunkRecord, Hit, ScoredHit

TODAY = date(2026, 9, 21)


@pytest.fixture
def today() -> date:
    return TODAY


@pytest.fixture
def ids():
    """A fresh chunk/document id sequence per test -- state is not shared across tests."""
    return count(1)


def _scored(chunk_id: int, document_id: int, score: float, *, specificity: float = 0.25,
            identifier: str | None = None, event_date: date | None = None) -> ScoredHit:
    chunk = ChunkRecord(
        chunk_id=chunk_id, document_id=document_id, ordinal=0, text_original="o", text_en="e",
        heading_path="", anchor=None, extent_id="CH", authority=Authority.OFFICIAL_INFO,
        categories=(), url="u", identifier=identifier, title_original="t", title_en="t",
        language="de", valid_from=None, retrieved_at=datetime(2026, 1, 1, tzinfo=UTC), license=None,
        source_id="s", event_date=event_date,
    )
    hit = Hit(chunk=chunk, rrf_score=0.0, dense_rank=None, lexical_rank=None)
    return ScoredHit(hit=hit, score=score, specificity=specificity, category_overlap=0, authority_score=0)


def scored_event(ids: count, series: str, days_ahead: int, *, score: float | None = None,
                  specificity: float = 0.25) -> ScoredHit:
    """An upcoming hit in ``series``, ranked higher the nearer it is by default -- like the
    reranker's nearest-future-first ordering for calendar evidence. ``score`` and
    ``specificity`` can be overridden to force a specific chunk into the role of "most
    specific" or "highest ranked"."""
    chunk_id = next(ids)
    event_date = TODAY + timedelta(days=days_ahead)
    resolved_score = 0.9 - days_ahead * 0.01 if score is None else score
    return _scored(
        chunk_id, document_id=chunk_id, score=resolved_score, specificity=specificity,
        identifier=f"{series}-{event_date.isoformat()}", event_date=event_date,
    )


def scored_chunk(ids: count, score: float) -> ScoredHit:
    """A non-calendar prose hit: no event date, no series."""
    chunk_id = next(ids)
    return _scored(chunk_id, document_id=chunk_id, score=score)


def sort_by_score(items):
    return tuple(sorted(items, key=lambda s: s.score, reverse=True))


def _upcoming_calendar_count(chosen, today: date) -> int:
    """How many of ``chosen`` are upcoming, identified calendar evidence -- exactly what
    UPCOMING_CALENDAR_CAP bounds. Deliberately not ``event_date is not None``: that predicate
    also matches past events and identifier-less event-dated chunks, neither of which this cap
    counts (see diversify.py's module docstring)."""
    return sum(1 for c in chosen if _capped_series(c, today) is not None)


def test_calendar_evidence_cannot_fill_an_answer(today, ids):
    """Five series of upcoming events must not crowd out non-calendar evidence."""
    events = [scored_event(ids, series=s, days_ahead=d) for s in
              ("waste", "organic", "cardboard", "mobile", "paper") for d in (1, 8, 15)]
    prose = [scored_chunk(ids, score=0.4) for _ in range(5)]
    chosen = diversify(sort_by_score(events + prose), limit=10, today=today)
    assert _upcoming_calendar_count(chosen, today) <= UPCOMING_CALENDAR_CAP
    assert any(c.hit.chunk.event_date is None for c in chosen)


def test_a_single_series_still_keeps_its_nearest_dates(today, ids):
    events = [scored_event(ids, series="cardboard", days_ahead=d) for d in (1, 8, 15, 22, 29)]
    chosen = diversify(events, limit=10, today=today)
    assert [c.hit.chunk.event_date for c in chosen] == sorted(c.hit.chunk.event_date for c in chosen)


def _two_series_at_the_ceiling_plus_one_blocked_series(ids):
    """Two series (waste, organic) fill the ceiling exactly at PER_SERIES_CAP each (6 total);
    one prose chunk ranks below all six; a third series (cardboard) ranks above prose but is
    blocked from ``_select`` entirely by the aggregate ceiling, and is the most specific chunk
    in the pool so ``diversify()`` tries to force it in afterwards."""
    waste = [scored_event(ids, series="waste", days_ahead=d) for d in (1, 8, 15)]
    organic = [scored_event(ids, series="organic", days_ahead=d) for d in (2, 9, 16)]
    prose = scored_chunk(ids, score=0.4)
    cardboard = scored_event(ids, series="cardboard", days_ahead=1, score=0.5, specificity=1.0)
    return sort_by_score([*waste, *organic, prose, cardboard])


def test_swap_path_respects_the_upcoming_calendar_ceiling(today, ids):
    """limit=7 makes ``_select`` fill ``chosen`` to exactly the limit (6 capped calendar chunks
    + 1 prose chunk), so ``len(chosen) < limit`` in the append branch is false regardless of
    that branch's calendar guard -- diversify() is forced into ``_swap_index`` to try to seat
    the blocked, most-specific cardboard chunk. ``_swap_index`` must not accept the first
    position it considers (the prose chunk) just because removing it is legal under the other
    two caps: removing a non-calendar chunk frees no calendar headroom, so seating cardboard
    there would push the ceiling to 7. It must instead look further back for a position that
    does free calendar headroom (an organic chunk)."""
    ranked = _two_series_at_the_ceiling_plus_one_blocked_series(ids)
    chosen = diversify(ranked, limit=7, today=today)
    assert _upcoming_calendar_count(chosen, today) <= UPCOMING_CALENDAR_CAP
    assert len(chosen) == 7


def test_append_path_respects_the_upcoming_calendar_ceiling(today, ids):
    """limit=10 leaves ``len(chosen) < limit`` true after ``_select`` (only 7 chunks were
    selectable), so this reaches the direct-append branch with room and both other caps
    satisfied. Its own calendar guard must still refuse to append the blocked, most-specific
    cardboard chunk on top of an already-full ceiling."""
    ranked = _two_series_at_the_ceiling_plus_one_blocked_series(ids)
    chosen = diversify(ranked, limit=10, today=today)
    assert _upcoming_calendar_count(chosen, today) <= UPCOMING_CALENDAR_CAP
    assert len(chosen) == 7
