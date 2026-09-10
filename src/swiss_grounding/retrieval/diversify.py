from typing import Sequence

from swiss_grounding.retrieval.models import ScoredHit


def diversify(
    ranked: Sequence[ScoredHit], limit: int, per_document_cap: int = 2,
) -> tuple[ScoredHit, ...]:
    """Cap chunks per document and guarantee the most specific extent is represented."""
    if not ranked:
        return ()
    chosen: list[ScoredHit] = []
    per_doc: dict[int, int] = {}
    for item in ranked:
        if len(chosen) >= limit:
            break
        doc = item.hit.chunk.document_id
        if per_doc.get(doc, 0) >= per_document_cap:
            continue
        chosen.append(item)
        per_doc[doc] = per_doc.get(doc, 0) + 1
    most_specific = max(ranked, key=lambda s: s.specificity)
    chosen_ids = {s.hit.chunk.chunk_id for s in chosen}
    if most_specific.hit.chunk.chunk_id not in chosen_ids:
        chosen = [*chosen[: max(limit - 1, 0)], most_specific]
    return tuple(chosen)
