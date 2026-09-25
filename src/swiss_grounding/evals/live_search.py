"""Adapters from the live search service to the robustness and consistency runners."""
from collections.abc import Callable
from functools import lru_cache

from swiss_grounding.db.connection import connect
from swiss_grounding.evals.consistency import Answer
from swiss_grounding.evals.robustness import Hit, hit_from_response
from swiss_grounding.serving.models import SearchRequest, SearchResponse
from swiss_grounding.serving.search_service import SearchService

LIMIT = 10


def _search(service: SearchService, question: str, locations: tuple[str, ...]) -> SearchResponse:
    return service.search(SearchRequest(question, locations, {}, None, LIMIT))


def hit_search(service: SearchService) -> Callable[[str, tuple[str, ...]], Hit]:
    return lambda q, locs: hit_from_response(_search(service, q, locs))


def answer_search(service: SearchService, database_url: str) -> Callable[[str, tuple[str, ...]], Answer]:
    """The top citation keyed by translation group and anchor, so language versions of one text agree."""
    @lru_cache(maxsize=None)
    def group_of(document_id: int) -> str | None:
        with connect(database_url) as conn:
            row = conn.execute("select translation_group_id from corpus.document where id = %s",
                               (document_id,)).fetchone()
        return row["translation_group_id"] if row else None

    def ask(question: str, locations: tuple[str, ...]) -> Answer:
        resp = _search(service, question, locations)
        top = next((p.citations[0] for p in resp.places if p.citations), None)
        if top is None:
            return Answer(resp.status, None)
        group = group_of(top.document_id) or f"doc{top.document_id}"
        return Answer(resp.status, f"{group}#{top.anchor}" if top.anchor else group)
    return ask
