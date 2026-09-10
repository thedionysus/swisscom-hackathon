from collections.abc import Sequence

from swiss_grounding.retrieval.models import ScoredHit


def _select(
    ranked: Sequence[ScoredHit], limit: int, per_document_cap: int,
) -> tuple[tuple[ScoredHit, ...], dict[int, int]]:
    """Greedy top-down pick honouring the per-document cap."""
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
    return tuple(chosen), per_doc


def _swap_index(
    chosen: Sequence[ScoredHit], per_doc: dict[int, int], document_id: int, per_document_cap: int,
) -> int | None:
    """Last position whose removal frees a slot for ``document_id`` under the cap."""
    for index in range(len(chosen) - 1, -1, -1):
        freed = chosen[index].hit.chunk.document_id
        count = per_doc.get(document_id, 0) - (1 if freed == document_id else 0)
        if count < per_document_cap:
            return index
    return None


def diversify(
    ranked: Sequence[ScoredHit], limit: int, per_document_cap: int = 2,
) -> tuple[ScoredHit, ...]:
    """Cap chunks per document and guarantee the most specific extent is represented."""
    if not ranked or limit <= 0:
        return ()
    chosen, per_doc = _select(ranked, limit, per_document_cap)
    most_specific = max(ranked, key=lambda s: s.specificity)
    if most_specific.hit.chunk.chunk_id in {s.hit.chunk.chunk_id for s in chosen}:
        return chosen
    document_id = most_specific.hit.chunk.document_id
    if len(chosen) < limit and per_doc.get(document_id, 0) < per_document_cap:
        return (*chosen, most_specific)
    index = _swap_index(chosen, per_doc, document_id, per_document_cap)
    if index is None:
        return chosen
    return (*chosen[:index], most_specific, *chosen[index + 1:])
