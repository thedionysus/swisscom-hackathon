from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date

from swiss_grounding.db.connection import connect
from swiss_grounding.locations.models import AmbiguousLocation, ResolvedLocation
from swiss_grounding.locations.question_scan import resolve_from_question
from swiss_grounding.locations.resolver import LocationResolver, Resolution, canton_label
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.categories import CATEGORY_IDS
from swiss_grounding.retrieval.as_of import as_of_rejection
from swiss_grounding.retrieval.cite import build_citation
from swiss_grounding.retrieval.coverage import coverage_rows, resolution_note
from swiss_grounding.retrieval.diversify import diversify
from swiss_grounding.retrieval.embedder import Embedder
from swiss_grounding.retrieval.models import QueryRequest, QueryResponse
from swiss_grounding.retrieval.no_evidence import no_evidence_message
from swiss_grounding.retrieval.query_text import build_search_query
from swiss_grounding.retrieval.rerank import RerankWeights, rerank
from swiss_grounding.retrieval.search import (
    earliest_indexed_version,
    hybrid_search,
    path_evidence,
)
from swiss_grounding.retrieval.topics import resolve_topics, topic_decided_by

CANDIDATE_TOP_N = 50
MAX_LIMIT = 25
NEEDS_LOCATION_MESSAGE = (
    "No location was given and none was recognised in the question. "
    "Ask the user which city, canton, or postal code they are interested in, then search again."
)


def _validate(request: QueryRequest) -> QueryResponse | None:
    """Reject malformed requests up front. Out-of-range limits are clamped, not rejected.

    Pure, and it stays that way: `as_of` is the one field whose validity is a property of
    the corpus rather than of the request, so it is checked in `QueryCore._validate_as_of`
    where a connection is available, and not here.
    """
    if not request.question.strip():
        return QueryResponse(
            status="invalid_request", field="question",
            message="The question is empty. Provide the user's question text.",
        )
    # Both fields are validated, and named separately in the error, because a topic is
    # now a hard filter: an unknown id silently matches no chunk and would turn into an
    # unexplained `no_evidence` rather than a typo the caller can see and fix.
    for field, supplied in (("topics", request.topics), ("categories", request.categories)):
        unknown = sorted(c for c in supplied if c not in CATEGORY_IDS)
        if unknown:
            return QueryResponse(
                status="invalid_request", field=field,
                message=f"Unknown {field}: {unknown}. Call swiss_list_categories for valid ids.",
            )
    return None


@dataclass(frozen=True)
class QueryCore:
    database_url: str
    tree: LocationTree
    resolver: LocationResolver
    embedder: Embedder
    weights: RerankWeights
    today: Callable[[], date] = date.today

    def query(self, request: QueryRequest) -> QueryResponse:
        invalid = _validate(request)
        if invalid is not None:
            return invalid
        # Before resolving the location, so a request the index cannot answer for is
        # reported as the bad field it has rather than as `needs_location`: an `as_of`
        # the index cannot reach is unanswerable whatever the place turns out to be, and
        # answering `needs_location` first would send the caller round a loop fixing the
        # place only to be refused on the date afterwards.
        invalid = self._validate_as_of(request.as_of)
        if invalid is not None:
            return invalid
        resolved = self._resolve(request)
        if isinstance(resolved, AmbiguousLocation):
            labels = ", ".join(
                f"{c.label('en')} ({canton_label(self.tree, c)}, {c.id})" for c in resolved.candidates
            )
            return QueryResponse(
                status="needs_location",
                message=f"{resolved.input_text!r} is ambiguous ({resolved.reason}): {labels}. "
                        "Ask the user which one they mean, then search again.",
            )
        if resolved is None:
            text = request.location or ""
            message = (
                f"Could not resolve location {text!r}. Ask the user for a city, canton, or postal code."
                if text.strip() else NEEDS_LOCATION_MESSAGE
            )
            return QueryResponse(status="needs_location", message=message)
        limit = max(1, min(request.limit, MAX_LIMIT))
        today = request.as_of or self.today()
        # One split of the caller's text (ADR 0004): the English rendering for the dense
        # arm, the verbatim question for the lexical one. Built here and passed to both
        # arms and to the response, so the text that was embedded and the text the
        # response claims was embedded cannot disagree.
        query = build_search_query(request)
        # Empty means no constraint, not a constraint nothing satisfies; `search.FILTER`
        # and `topics.resolve_topics` both turn on that distinction. `resolve_topics`
        # rebuilds the same query for its classifier rung rather than taking it from here:
        # it owns its whole ladder, including which text it classifies, and the rebuild is
        # a strip and a join on three strings.
        topics = resolve_topics(request, self.embedder)
        with connect(self.database_url) as conn:
            hits = hybrid_search(
                conn, self.embedder, question=query.lexical, extent_path=resolved.path,
                as_of=request.as_of, top_n=CANDIDATE_TOP_N, topics=topics,
                embedded_question=query.dense,
            )
            # Deliberately not passed `topics`: coverage is about places, not subjects
            # (ADR 0001), and it is the same count `swiss_coverage` returns.
            rows = coverage_rows(conn, self.tree, resolved.path)
            # Only on the empty path, and only there: this is what lets `no_evidence`
            # establish which arm of the filter emptied the result instead of guessing
            # between them. The coverage rows above cannot answer that -- they count
            # documents, apply neither the topic nor the date, and cannot see a document
            # whose chunks are gone.
            evidence = None if hits else path_evidence(
                conn, resolved.path, as_of=request.as_of, topics=topics,
            )
        note = resolution_note(
            rows, self.tree, resolved.input_text, resolved.location, resolved.method, resolved.alternatives,
        )
        base = QueryResponse(
            status="no_evidence", resolved_location_id=resolved.location.id,
            resolved_location_label=resolved.location.label("en"),
            resolution_method=resolved.method,
            alternatives=tuple(a.id for a in resolved.alternatives),
            categories_used=topics,
            coverage=rows, resolution_note=note,
            query_fields=query.fields, topic_decided_by=topic_decided_by(request),
        )
        if not hits:
            return replace(base, message=no_evidence_message(
                resolved.location.label("en"), evidence, topics, request.as_of,
            ))
        # The same topics that filtered, not `request.categories`, so the soft signal and
        # the hard filter can never disagree about what this question is about. They are
        # identical for a caller on the old contract, which is every caller until Task 10.
        ranked = rerank(hits, self.tree, resolved.location.id, topics, self.weights,
                        today=lambda: today)
        # per_document_cap, per_series_cap, and upcoming_calendar_cap all take diversify()'s
        # own defaults here; there is no query_core-specific override.
        chosen = diversify(ranked, limit=limit, today=today)
        citations = tuple(build_citation(s, self.tree) for s in chosen)
        return replace(base, status="results", citations=citations)

    def _validate_as_of(self, as_of: date | None) -> QueryResponse | None:
        """Refuse an `as_of` the index cannot reach back to (D2, `retrieval/as_of.py`).

        This is the one boundary check that cannot live in `_validate`: the earliest
        answerable date is a property of the corpus, so it has to be queried. Rather than
        make `_validate` impure or thread a date through it, the query runs here, under a
        connection of its own, and only for a request that actually carries a date -- the
        rare case. That keeps the cost off every undated query and keeps the whole of
        `query` from having to be re-indented inside one long-lived connection.
        """
        if as_of is None:
            return None
        with connect(self.database_url) as conn:
            earliest = earliest_indexed_version(conn)
        rejection = as_of_rejection(as_of, earliest)
        if rejection is None:
            return None
        return QueryResponse(
            status="invalid_request", field="as_of", message=rejection.message,
        )

    def _resolve(self, request: QueryRequest) -> Resolution:
        if request.location and request.location.strip():
            return self.resolver.resolve(request.location)
        return self._resolve_from_question(request.question)

    def _resolve_from_question(self, question: str) -> ResolvedLocation | None:
        return resolve_from_question(self.tree, question)
