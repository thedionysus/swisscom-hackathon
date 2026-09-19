from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date

from swiss_grounding.db.connection import connect
from swiss_grounding.locations.models import AmbiguousLocation, ResolvedLocation
from swiss_grounding.locations.question_scan import resolve_from_question
from swiss_grounding.locations.resolver import LocationResolver, Resolution, canton_label
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.categories import CATEGORY_IDS
from swiss_grounding.retrieval.cite import build_citation
from swiss_grounding.retrieval.coverage import coverage_rows, resolution_note
from swiss_grounding.retrieval.diversify import diversify
from swiss_grounding.retrieval.embedder import Embedder
from swiss_grounding.retrieval.models import QueryRequest, QueryResponse
from swiss_grounding.retrieval.rerank import RerankWeights, rerank
from swiss_grounding.retrieval.search import hybrid_search

CANDIDATE_TOP_N = 50
PER_DOCUMENT_CAP = 2
MAX_LIMIT = 25
NEEDS_LOCATION_MESSAGE = (
    "No location was given and none was recognised in the question. "
    "Ask the user which city, canton, or postal code they are interested in, then search again."
)


def _validate(request: QueryRequest) -> QueryResponse | None:
    """Reject malformed requests up front. Out-of-range limits are clamped, not rejected."""
    if not request.question.strip():
        return QueryResponse(
            status="invalid_request", field="question",
            message="The question is empty. Provide the user's question text.",
        )
    unknown = sorted(c for c in request.categories if c not in CATEGORY_IDS)
    if unknown:
        return QueryResponse(
            status="invalid_request", field="categories",
            message=f"Unknown categories: {unknown}. Call swiss_list_categories for valid ids.",
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
        with connect(self.database_url) as conn:
            hits = hybrid_search(
                conn, self.embedder, question=request.question, extent_path=resolved.path,
                as_of=request.as_of, top_n=CANDIDATE_TOP_N,
            )
            rows = coverage_rows(conn, self.tree, resolved.path)
        note = resolution_note(
            rows, resolved.method, [f"{a.label('en')} ({a.level.value})" for a in resolved.alternatives],
        )
        base = QueryResponse(
            status="no_evidence", resolved_location_id=resolved.location.id,
            resolved_location_label=resolved.location.label("en"),
            resolution_method=resolved.method,
            alternatives=tuple(a.id for a in resolved.alternatives),
            categories_used=request.categories,
            coverage=rows, resolution_note=note,
        )
        if not hits:
            label = resolved.location.label("en")
            return replace(base, message=f"No indexed evidence for {label} or its parent jurisdictions.")
        ranked = rerank(hits, self.tree, resolved.location.id, request.categories, self.weights,
                        today=self.today)
        chosen = diversify(ranked, limit=limit, per_document_cap=PER_DOCUMENT_CAP)
        citations = tuple(build_citation(s, self.tree) for s in chosen)
        return replace(base, status="results", citations=citations)

    def _resolve(self, request: QueryRequest) -> Resolution:
        if request.location and request.location.strip():
            return self.resolver.resolve(request.location)
        return self._resolve_from_question(request.question)

    def _resolve_from_question(self, question: str) -> ResolvedLocation | None:
        return resolve_from_question(self.tree, question)
