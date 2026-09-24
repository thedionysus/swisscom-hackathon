from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime

from swiss_grounding.retrieval.calendar import calendar_series
from swiss_grounding.retrieval.models import ScoredHit

PER_DOCUMENT_CAP = 2
PER_SERIES_CAP = 3
UPCOMING_CALENDAR_CAP = 6


def _capped_series(item: ScoredHit, today: date) -> str | None:
    """The calendar series a chunk is capped under, or None when the cap does not apply.

    Only *upcoming* occurrences of a series are capped: a series such as cardboard collection
    floods the candidate pool with one document per future date, and that flood is what
    crowds out other evidence. A chunk with no event date, no identifier, or an event date
    already in the past is never capped by this rule. The reranker applies only a
    multiplicative penalty to a past event (``PAST_EVENT_PENALTY`` in ``rerank.py``), not a
    hard floor, so a past event can still outrank some future ones on score alone -- but a
    series has no bound on how many future occurrences exist, and without this exemption a
    heavily-recurring series could fill its cap with future dates ahead of the one past event
    a question is actually about, which defeats the point of asking about it.

    A chunk carrying an ``event_date`` but no ``identifier`` is invisible to every cap built
    on this function, same as a past event: it has no series to be counted under. No source
    in the live schema produces that combination today, and nothing here validates against it.
    """
    chunk = item.hit.chunk
    if chunk.event_date is None or chunk.event_date < today:
        return None
    return calendar_series(chunk.identifier)


@dataclass(frozen=True)
class Caps:
    """The three ceilings ``diversify()`` enforces together."""
    per_document: int
    per_series: int
    upcoming_calendar: int


@dataclass(frozen=True)
class _Tally:
    """Running counts against a ``Caps`` ceiling. Immutable: ``plus`` and ``minus`` return a
    new ``_Tally`` rather than changing this one, so a hypothetical removal (for a swap) never
    disturbs the tally anyone else is holding.

    ``per_series`` only ever holds counts for series ``_capped_series`` names -- upcoming,
    identified calendar evidence -- so ``sum(per_series.values())`` is exactly the amount of
    *that* evidence counted so far, across every series combined.
    """
    caps: Caps
    today: date
    per_doc: dict[int, int]
    per_series: dict[str, int]

    def fits(self, item: ScoredHit) -> bool:
        """Would adding ``item`` stay within every cap?"""
        doc = item.hit.chunk.document_id
        if self.per_doc.get(doc, 0) >= self.caps.per_document:
            return False
        series = _capped_series(item, self.today)
        if series is None:
            return True
        if self.per_series.get(series, 0) >= self.caps.per_series:
            return False
        return sum(self.per_series.values()) < self.caps.upcoming_calendar

    def plus(self, item: ScoredHit) -> "_Tally":
        """The tally after adding ``item``."""
        doc = item.hit.chunk.document_id
        per_doc = {**self.per_doc, doc: self.per_doc.get(doc, 0) + 1}
        series = _capped_series(item, self.today)
        per_series = self.per_series if series is None else {
            **self.per_series, series: self.per_series.get(series, 0) + 1,
        }
        return replace(self, per_doc=per_doc, per_series=per_series)

    def minus(self, item: ScoredHit) -> "_Tally":
        """The tally as if ``item`` had never been added -- used to ask "if I freed this
        position, would the candidate then fit?" without touching the tally itself."""
        doc = item.hit.chunk.document_id
        per_doc = {**self.per_doc, doc: self.per_doc.get(doc, 0) - 1}
        series = _capped_series(item, self.today)
        per_series = self.per_series if series is None else {
            **self.per_series, series: self.per_series.get(series, 0) - 1,
        }
        return replace(self, per_doc=per_doc, per_series=per_series)


def _select(
    ranked: Sequence[ScoredHit], limit: int, caps: Caps, today: date,
) -> tuple[tuple[ScoredHit, ...], _Tally]:
    """Greedy top-down pick honouring every cap in ``caps``."""
    chosen: list[ScoredHit] = []
    tally = _Tally(caps=caps, today=today, per_doc={}, per_series={})
    for item in ranked:
        if len(chosen) >= limit:
            break
        if not tally.fits(item):
            continue
        chosen.append(item)
        tally = tally.plus(item)
    return tuple(chosen), tally


def _swap_index(chosen: Sequence[ScoredHit], tally: _Tally, candidate: ScoredHit) -> int | None:
    """Last position whose removal frees a slot for ``candidate`` under every cap in ``tally``.

    Freeing a position that doesn't itself count toward one of ``candidate``'s caps (e.g. a
    non-calendar chunk, when ``candidate`` is upcoming calendar evidence) frees no headroom for
    that cap, so ``tally.minus(...).fits(...)`` correctly rejects it and this keeps scanning.
    """
    for index in range(len(chosen) - 1, -1, -1):
        if tally.minus(chosen[index]).fits(candidate):
            return index
    return None


def diversify(
    ranked: Sequence[ScoredHit], limit: int, per_document_cap: int = PER_DOCUMENT_CAP,
    per_series_cap: int = PER_SERIES_CAP, upcoming_calendar_cap: int = UPCOMING_CALENDAR_CAP,
    today: date | None = None,
) -> tuple[ScoredHit, ...]:
    """Cap chunks per document, per calendar series, and across upcoming calendar evidence as
    a whole, and guarantee the most specific extent is represented.

    The per-document cap limits repeated chunks from the same document; the per-series cap
    limits repeated *upcoming* calendar events (one document per date) that share a series,
    such as every future cardboard collection date, so a page of near-identical future events
    cannot crowd out everything else. Both only apply to a chunk carrying an ``event_date``
    that has not already passed *and* a non-empty ``identifier`` (see ``_capped_series``);
    ``today`` defaults to the real current date.

    The per-series cap alone cannot bound calendar evidence overall: several series can each
    have upcoming events (waste, organic, cardboard, mobile, paper collections all repeat
    independently), so several series at the per-series cap can still add up to more than a
    caller's requested limit and fill an answer with nothing but dates. ``upcoming_calendar_cap``
    is that aggregate ceiling, summed across every series, with the same upcoming-and-identified
    scope as the per-series cap -- a past event never counts against it, by design: a question
    about a missed collection must still be able to find that collection. This leaves past
    calendar evidence and an identifier-less event-dated chunk unbounded here; both are
    deliberate scope cuts, not oversights.

    ``upcoming_calendar_cap``'s default of 6 is a judgement call, not derived from a probe: no
    current probe constrains it from below. Concretely, since ``QueryRequest.limit`` defaults
    to 8, calendar evidence can still take up to 6 of 8 citations in a default-sized answer.
    """
    if not ranked or limit <= 0:
        return ()
    current = today if today is not None else datetime.now(tz=UTC).date()
    caps = Caps(per_document=per_document_cap, per_series=per_series_cap,
                upcoming_calendar=upcoming_calendar_cap)
    chosen, tally = _select(ranked, limit, caps, current)
    most_specific = max(ranked, key=lambda s: s.specificity)
    if most_specific.hit.chunk.chunk_id in {s.hit.chunk.chunk_id for s in chosen}:
        return chosen
    if len(chosen) < limit and tally.fits(most_specific):
        return (*chosen, most_specific)
    index = _swap_index(chosen, tally, most_specific)
    if index is None:
        return chosen
    return (*chosen[:index], most_specific, *chosen[index + 1:])
