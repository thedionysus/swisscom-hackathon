import re
from dataclasses import dataclass, replace

from swiss_grounding.db.connection import connect
from swiss_grounding.locations.models import ResolvedLocation
from swiss_grounding.locations.resolver import LocationResolver
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.categories import CATEGORY_IDS
from swiss_grounding.retrieval.cite import build_citation
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
WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9.\-]*")


@dataclass(frozen=True)
class QueryCore:
    database_url: str
    tree: LocationTree
    resolver: LocationResolver
    embedder: Embedder
    weights: RerankWeights

    def query(self, request: QueryRequest) -> QueryResponse:
        if not request.question.strip():
            return QueryResponse(status="needs_location", message="The question is empty.")
        unknown = [c for c in request.categories if c not in CATEGORY_IDS]
        if unknown:
            return QueryResponse(status="needs_location", message=f"Unknown categories: {unknown}")
        resolved = self._resolve(request)
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
        base = QueryResponse(
            status="no_evidence", resolved_location_id=resolved.location.id,
            resolved_location_label=resolved.location.label("en"),
            resolution_method=resolved.method,
            alternatives=tuple(a.id for a in resolved.alternatives),
            categories_used=request.categories,
        )
        if not hits:
            label = resolved.location.label("en")
            return replace(base, message=f"No indexed evidence for {label} or its parent jurisdictions.")
        ranked = rerank(hits, self.tree, resolved.location.id, request.categories, self.weights)
        chosen = diversify(ranked, limit=limit, per_document_cap=PER_DOCUMENT_CAP)
        citations = tuple(build_citation(s, self.tree) for s in chosen)
        return replace(base, status="results", citations=citations)

    def _resolve(self, request: QueryRequest) -> ResolvedLocation | None:
        if request.location and request.location.strip():
            return self.resolver.resolve(request.location)
        return self._resolve_from_question(request.question)

    def _resolve_from_question(self, question: str) -> ResolvedLocation | None:
        """Alias-only scan of the question text, longest n-gram first. Never calls GeoAdmin.

        1-gram candidates are restricted to words that are capitalized in the
        original question or are all digits (postal codes), to avoid spurious
        matches against short lowercase canton-abbreviation aliases (e.g. "be",
        "so", "ai", "ur") that can appear as ordinary English words.
        """
        words = WORD_RE.findall(question)
        for size in (3, 2, 1):
            for start in range(0, max(0, len(words) - size + 1)):
                span = words[start:start + size]
                candidate = " ".join(span).rstrip("?.,!")
                if size == 1 and not (candidate[:1].isupper() or candidate.isdigit()):
                    continue
                matches = self.tree.find(candidate)
                if matches:
                    best = matches[0]
                    return ResolvedLocation(
                        location=best, path=self.tree.path(best.id), method="alias_in_question",
                        input_text=candidate, alternatives=tuple(matches[1:]),
                    )
        return None
