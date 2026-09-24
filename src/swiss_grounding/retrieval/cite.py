from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.retrieval.models import Citation, ScoredHit

SNIPPET_CHARS = 600
# Four decimals on the published distance. Enough to order two chunks apart on the
# measured spread (0.5115 against 0.5257 on the Dietikon forest question), short enough
# that a float's trailing noise does not make two identical answers look different.
DISTANCE_PLACES = 4


def _snippet(text: str) -> str:
    return text if len(text) <= SNIPPET_CHARS else text[: SNIPPET_CHARS - 1] + "…"


def _distance(scored: ScoredHit) -> float | None:
    """The published distance, rounded. `None` stays `None`: an unmeasured distance is not
    a far one, and rounding it into a number would hide that from the caller."""
    raw = scored.hit.distance
    return None if raw is None else round(raw, DISTANCE_PLACES)


def build_citation(scored: ScoredHit, tree: LocationTree) -> Citation:
    """The caller-facing record for one ranked hit.

    It publishes `tier` and `distance` rather than `score`. Both are
    lower-is-better and both may be `None`; `models.Citation` documents what that means.
    """
    c = scored.hit.chunk
    return Citation(
        chunk_id=c.chunk_id, document_id=c.document_id, source_id=c.source_id,
        title_en=c.title_en, title_original=c.title_original, url=c.url, anchor=c.anchor,
        identifier=c.identifier, snippet_en=_snippet(c.text_en),
        snippet_original=_snippet(c.text_original), language=c.language,
        heading_path=c.heading_path, extent_id=c.extent_id,
        extent_label=tree.get(c.extent_id).label("en"), authority=c.authority.value,
        categories=c.categories, valid_from=c.valid_from, retrieved_at=c.retrieved_at,
        license=c.license, tier=scored.tier, distance=_distance(scored),
        event_date=c.event_date,
    )
