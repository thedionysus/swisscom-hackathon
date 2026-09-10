from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.retrieval.models import Citation, ScoredHit

SNIPPET_CHARS = 600


def _snippet(text: str) -> str:
    return text if len(text) <= SNIPPET_CHARS else text[: SNIPPET_CHARS - 1] + "…"


def build_citation(scored: ScoredHit, tree: LocationTree) -> Citation:
    c = scored.hit.chunk
    return Citation(
        chunk_id=c.chunk_id, document_id=c.document_id, source_id=c.source_id,
        title_en=c.title_en, title_original=c.title_original, url=c.url, anchor=c.anchor,
        identifier=c.identifier, snippet_en=_snippet(c.text_en),
        snippet_original=_snippet(c.text_original), language=c.language,
        heading_path=c.heading_path, extent_id=c.extent_id,
        extent_label=tree.get(c.extent_id).label("en"), authority=c.authority.value,
        categories=c.categories, valid_from=c.valid_from, retrieved_at=c.retrieved_at,
        license=c.license, score=round(scored.score, 4),
    )
