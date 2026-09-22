from collections.abc import Sequence
from datetime import UTC, date, datetime

from swiss_grounding.retrieval.calendar import calendar_series
from swiss_grounding.retrieval.models import ScoredHit

PER_SERIES_CAP = 3
UPCOMING_CALENDAR_CAP = 6


def _capped_series(item: ScoredHit, today: date) -> str | None:
    """The calendar series a chunk is capped under, or None when the cap does not apply.

    Only *upcoming* occurrences of a series are capped: a series such as cardboard collection
    floods the candidate pool with one document per future date, and that flood is what
    crowds out other evidence. A chunk with no event date, no identifier, or an event date
    already in the past is never capped by this rule -- the reranker already sinks past
    events below future ones, so without this exemption a past event would never win a slot
    in its own series' cap and would stay unreachable, which defeats the point of asking
    about it.

    A chunk carrying an ``event_date`` but no ``identifier`` is invisible to every cap built
    on this function, same as a past event: it has no series to be counted under. No source
    in the live schema produces that combination today, and nothing here validates against it.
    """
    chunk = item.hit.chunk
    if chunk.event_date is None or chunk.event_date < today:
        return None
    return calendar_series(chunk.identifier)


def _select(
    ranked: Sequence[ScoredHit], limit: int, per_document_cap: int, per_series_cap: int,
    upcoming_calendar_cap: int, today: date,
) -> tuple[tuple[ScoredHit, ...], dict[int, int], dict[str, int]]:
    """Greedy top-down pick honouring the per-document, per-series, and upcoming-calendar-
    aggregate caps.

    ``per_series`` only ever holds counts for series that ``_capped_series`` returns a name
    for -- upcoming, identified calendar evidence -- so ``sum(per_series.values())`` is
    exactly the amount of *that* evidence chosen so far, across every series combined. It
    says nothing about past events or event-dated chunks without an identifier: neither is
    counted here, by the same exemption ``_capped_series`` documents.
    """
    chosen: list[ScoredHit] = []
    per_doc: dict[int, int] = {}
    per_series: dict[str, int] = {}
    for item in ranked:
        if len(chosen) >= limit:
            break
        doc = item.hit.chunk.document_id
        if per_doc.get(doc, 0) >= per_document_cap:
            continue
        series = _capped_series(item, today)
        if series is not None:
            if per_series.get(series, 0) >= per_series_cap:
                continue
            if sum(per_series.values()) >= upcoming_calendar_cap:
                continue
        chosen.append(item)
        per_doc[doc] = per_doc.get(doc, 0) + 1
        if series is not None:
            per_series[series] = per_series.get(series, 0) + 1
    return tuple(chosen), per_doc, per_series


def _swap_index(
    chosen: Sequence[ScoredHit], per_doc: dict[int, int], per_series: dict[str, int],
    candidate: ScoredHit, per_document_cap: int, per_series_cap: int, upcoming_calendar_cap: int,
    today: date,
) -> int | None:
    """Last position whose removal frees a slot for ``candidate`` under all three caps.

    A candidate that is itself upcoming calendar evidence must not be swapped in past the
    upcoming-calendar-aggregate ceiling, even when the position it displaces held a
    non-calendar chunk: freeing a non-calendar slot never frees calendar headroom.
    """
    document_id = candidate.hit.chunk.document_id
    series = _capped_series(candidate, today)
    calendar_total = sum(per_series.values())
    for index in range(len(chosen) - 1, -1, -1):
        freed = chosen[index]
        freed_doc = freed.hit.chunk.document_id
        freed_series = _capped_series(freed, today)
        doc_count = per_doc.get(document_id, 0) - (1 if freed_doc == document_id else 0)
        series_count = (
            per_series.get(series, 0) - (1 if freed_series == series else 0)
            if series is not None else 0
        )
        calendar_count = calendar_total - (1 if freed_series is not None else 0)
        fits_calendar = series is None or calendar_count < upcoming_calendar_cap
        if doc_count < per_document_cap and series_count < per_series_cap and fits_calendar:
            return index
    return None


def diversify(
    ranked: Sequence[ScoredHit], limit: int, per_document_cap: int = 2,
    per_series_cap: int = PER_SERIES_CAP, upcoming_calendar_cap: int = UPCOMING_CALENDAR_CAP,
    today: date | None = None,
) -> tuple[ScoredHit, ...]:
    """Cap chunks per document, per calendar series, and across upcoming calendar evidence as
    a whole, and guarantee the most specific extent is represented.

    The per-document cap limits repeated chunks from the same document; the per-series cap
    limits repeated *upcoming* calendar events (one document per date) that share a series,
    such as every future cardboard collection date, so a page of near-identical future
    events cannot crowd out everything else. Both only apply to chunks carrying an
    ``event_date`` that has not already passed; ``today`` defaults to the real current date.

    The per-series cap alone cannot bound calendar evidence overall: several series can each
    have upcoming events (waste, organic, cardboard, mobile, paper collections all repeat
    independently), so several series at the per-series cap can still add up to more than a
    caller's requested limit and fill an answer with nothing but dates. ``upcoming_calendar_cap``
    is that aggregate ceiling, summed across every series -- but, like the per-series cap, it
    only counts *upcoming* calendar evidence (see ``_capped_series``). A past event never
    counts against it, by design: a question about a missed collection must still be able to
    find that collection. This deliberately leaves two things unbounded here: a pile of *past*
    calendar evidence (a different risk than the one this cap was built against -- the reranker
    already sinks past events to the bottom, but nothing yet stops many of them from filling an
    answer) and a chunk with an ``event_date`` but no ``identifier`` (invisible to every
    calendar cap, per ``_capped_series``; no such chunk exists in the live corpus today). Task
    8's hard topic filter is the intended defence for off-topic calendar evidence generally;
    this cap only targets the measured cause of Task 3, upcoming multi-series flooding.
    """
    if not ranked or limit <= 0:
        return ()
    current = today if today is not None else datetime.now(tz=UTC).date()
    chosen, per_doc, per_series = _select(
        ranked, limit, per_document_cap, per_series_cap, upcoming_calendar_cap, current,
    )
    most_specific = max(ranked, key=lambda s: s.specificity)
    if most_specific.hit.chunk.chunk_id in {s.hit.chunk.chunk_id for s in chosen}:
        return chosen
    document_id = most_specific.hit.chunk.document_id
    series = _capped_series(most_specific, current)
    fits_document = per_doc.get(document_id, 0) < per_document_cap
    fits_series = series is None or per_series.get(series, 0) < per_series_cap
    fits_calendar = series is None or sum(per_series.values()) < upcoming_calendar_cap
    if len(chosen) < limit and fits_document and fits_series and fits_calendar:
        return (*chosen, most_specific)
    index = _swap_index(
        chosen, per_doc, per_series, most_specific, per_document_cap, per_series_cap,
        upcoming_calendar_cap, current,
    )
    if index is None:
        return chosen
    return (*chosen[:index], most_specific, *chosen[index + 1:])
