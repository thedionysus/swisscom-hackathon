"""swiss_search: places → candidates → groups → reranker → relevance → status → citations."""
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np

from swiss_grounding.db.connection import connect
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.candidates import ArmQuery, gather_candidates
from swiss_grounding.serving.coverage import coverage_rows
from swiss_grounding.serving.groups import aligned_versions, collapse
from swiss_grounding.serving.language import detect_language
from swiss_grounding.serving.models import (
    Citation,
    GroupHit,
    PlaceResult,
    ScoredGroup,
    SearchRequest,
    SearchResponse,
    overall_status,
)
from swiss_grounding.serving.passages import best_passage
from swiss_grounding.serving.places import PlaceOutcome, Resolver, place_outcomes
from swiss_grounding.serving.relevance import Relevance, feature_vector
from swiss_grounding.serving.reranker import Reranker, passage_text
from swiss_grounding.serving.scope import scope_statement
from swiss_grounding.serving.status import decide, pre_search, uncovered_levels

Embedded = tuple[np.ndarray, dict[int, float] | None]
EmbedFn = Callable[[Sequence[str]], list[Embedded]]
RerankCache = dict[tuple[int, str], float]
WORDS = re.compile(r"\w+")
EMPTY_QUESTION = "The question is empty. Send the user's question as they wrote it."


def _normalised(text: str) -> str:
    return " ".join(WORDS.findall(text.lower()))


def distinct_citations(scored: Sequence[ScoredGroup]) -> list[ScoredGroup]:
    """Drop repeats before citing: the same text published under another URL (ch.ch serves many
    pages at two addresses), and another language version of a page already cited (HTML sections
    do not align across languages, so their chunks form separate groups)."""
    seen_text: set[str] = set()
    cited_language: dict[str, str] = {}
    kept = []
    for s in scored:
        rep = s.group.representative
        text = _normalised(rep.text)
        language = cited_language.get(rep.translation_group_id)
        if text in seen_text or (language is not None and language != rep.language):
            continue
        seen_text.add(text)
        cited_language[rep.translation_group_id] = rep.language
        kept.append(s)
    return kept


def query_embedder(provider) -> EmbedFn:
    """bge-m3 gives dense + sparse; any other provider gives dense only."""
    if hasattr(provider, "embed_with_sparse"):
        return provider.embed_with_sparse
    return lambda texts: [(v, None) for v in provider.embed(texts)]


@dataclass(frozen=True)
class _Query:
    request: SearchRequest
    lang: str | None
    vec: np.ndarray
    sparse: dict[int, float] | None
    translation_vecs: dict[str, np.ndarray]


@dataclass(frozen=True)
class SearchService:
    database_url: str
    tree: LocationTree
    resolver: Resolver
    embed: EmbedFn
    reranker: Reranker
    relevance: Relevance
    index: str
    rerank_candidates: int
    local_quota: int
    ef_search: int
    today: Callable[[], date] = date.today

    def search(self, request: SearchRequest) -> SearchResponse:
        if not request.question.strip():
            return SearchResponse("invalid_request", (), message=EMPTY_QUESTION, field="question")
        outcomes = place_outcomes(request.question, request.locations, self.resolver, self.tree)
        decided = [pre_search(o) for o in outcomes]
        query = self._embed(request) if any(d is None for d in decided) else None
        cache: RerankCache = {}   # reranker scores, shared by the places of one request
        places = tuple(d if d is not None else self._place(o, query, cache)
                       for o, d in zip(outcomes, decided, strict=True))
        status = overall_status([p.status for p in places])
        needs_scope = any(p.status in ("no_evidence", "outside_scope") for p in places)
        return SearchResponse(status, places, scope=scope_statement() if needs_scope else "")

    def _embed(self, request: SearchRequest) -> _Query:
        langs = list(request.translations)
        embedded = self.embed([request.question, *(request.translations[lang] for lang in langs)])
        vec, sparse = embedded[0]
        tvecs = {lang: embedded[i + 1][0] for i, lang in enumerate(langs)}
        return _Query(request, detect_language(request.question), vec, sparse, tvecs)

    def _scope_path(self, o: PlaceOutcome) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """The path searched (cut at the last covered level) and its local part (everything below CH)."""
        if o.kind != "resolved" or o.resolved is None:
            return (), ()
        full = o.resolved.path
        path = full if "municipal" in o.covered else full[: len(o.covered)]
        return path, path[1:]

    def _place(self, o: PlaceOutcome, q: _Query, cache: RerankCache) -> PlaceResult:
        path, local = self._scope_path(o)
        arm = ArmQuery(q.request.question, q.lang, q.vec, q.sparse, q.request.translations, q.translation_vecs,
                       path, local, q.request.as_of, self.rerank_candidates, self.rerank_candidates,
                       self.local_quota if local else 0)
        with connect(self.database_url) as conn:
            cands = gather_candidates(conn, arm, index=self.index, ef_search=self.ef_search)
            keys = list(dict.fromkeys((c.translation_group_id, c.align_key) for c in cands))
            versions = aligned_versions(conn, keys, q.request.as_of)
            coverage = coverage_rows(conn, self.tree, path) if path else ()
        scored = self._score(collapse(cands, versions, q.lang), q, path, cache)
        status, message = decide(o, scored, threshold=self.relevance.threshold, tree=self.tree)
        citations = ()
        if status == "results":
            queries = [q.request.question, *q.request.translations.values()]
            relevant = [s for s in scored if s.relevance >= self.relevance.threshold]
            if o.kind == "none":
                # A placeless answer cites federal evidence only: cantonal and municipal passages
                # apply to one place and would mislead a user elsewhere (ADR 0013).
                relevant = [s for s in relevant if s.group.representative.extent_id == "CH"]
            keep = distinct_citations(relevant)[: q.request.limit]
            citations = tuple(self._cite(s, queries) for s in keep)
        loc = o.resolved.location if o.resolved else None
        return PlaceResult(o.text, status, loc.id if loc else None, loc.label("de") if loc else None,
                           message, citations, coverage, uncovered_levels(o))

    def _tier(self, extent: str, path: Sequence[str]) -> int | None:
        """0 for the place's own extent, rising towards CH; None when the extent is off the path."""
        return len(path) - 1 - path.index(extent) if extent in path else None

    def _rerank(self, question: str, groups: Sequence[GroupHit], cache: RerankCache) -> list[float]:
        """Reranker scores of the groups' representatives, scoring only those not already cached."""
        reps = [g.representative for g in groups]
        missing = [r for r in reps if (r.chunk_id, r.language) not in cache]
        fresh = self.reranker.score(question, [passage_text(r.breadcrumb, r.text) for r in missing])
        cache.update({(r.chunk_id, r.language): v for r, v in zip(missing, fresh, strict=True)})
        return [cache[(r.chunk_id, r.language)] for r in reps]

    def _score(self, groups: list[GroupHit], q: _Query, path: Sequence[str],
               cache: RerankCache) -> list[ScoredGroup]:
        scores = self._rerank(q.request.question, groups, cache)
        today = q.request.as_of or self.today()
        out = []
        for g, score in zip(groups, scores, strict=True):
            tier = self._tier(g.representative.extent_id, path)
            x = feature_vector(g, rerank_score=score, question_lang=q.lang, tier=tier, today=today)
            out.append(ScoredGroup(g, score, self.relevance.probability(x, rerank_score=score), tier))
        return sorted(out, key=lambda s: -s.relevance)

    def scored_for_eval(self, request: SearchRequest) -> list[tuple[tuple[float, ...], str]]:
        """(features, citation key) of every scored group, for every place of the request; evals only."""
        out = []
        q = self._embed(request)
        for outcome in place_outcomes(request.question, request.locations, self.resolver, self.tree):
            if pre_search(outcome) is None:
                out.extend(self._eval_rows(outcome, q, request))
        return out

    def _eval_rows(self, outcome: PlaceOutcome, q: _Query, request: SearchRequest):
        path, local = self._scope_path(outcome)
        arm = ArmQuery(request.question, q.lang, q.vec, q.sparse, request.translations, q.translation_vecs, path,
                       local, request.as_of, self.rerank_candidates, self.rerank_candidates,
                       self.local_quota if local else 0)
        with connect(self.database_url) as conn:
            cands = gather_candidates(conn, arm, index=self.index, ef_search=self.ef_search)
            versions = aligned_versions(conn, list(dict.fromkeys((c.translation_group_id, c.align_key)
                                                                 for c in cands)), request.as_of)
        groups = collapse(cands, versions, q.lang)
        reps = [g.representative for g in groups]
        scores = self.reranker.score(request.question, [passage_text(r.breadcrumb, r.text) for r in reps])
        today = request.as_of or self.today()
        rows = []
        for g, score in zip(groups, scores, strict=True):
            rep = g.representative
            x = feature_vector(g, rerank_score=score, question_lang=q.lang, tier=self._tier(rep.extent_id, path),
                               today=today)
            rows.append((x, f"{rep.url}#{rep.anchor}" if rep.anchor else rep.url))
        return rows

    def _cite(self, s: ScoredGroup, queries: Sequence[str]) -> Citation:
        g, rep = s.group, s.group.representative
        return Citation(
            chunk_id=rep.chunk_id, document_id=rep.document_id, title=rep.title, url=rep.url, anchor=rep.anchor,
            breadcrumb=rep.breadcrumb, passage=best_passage(rep.text, queries), language=rep.language,
            other_languages=tuple(sorted({o.language for o in g.others})), publisher=rep.publisher,
            authority=rep.authority, extent_id=rep.extent_id, extent_label=self.tree.get(rep.extent_id).label("de"),
            tier=s.tier, relevance=round(s.relevance, 4), corroboration=g.corroboration,
            corroboration_basis=g.corroboration_basis, versions_diverge=g.versions_diverge,
            valid_from=rep.valid_from, modified_at=rep.modified_at, fetched_at=rep.fetched_at,
            extraction=rep.extraction)
