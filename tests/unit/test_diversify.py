from datetime import datetime

from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.diversify import diversify
from swiss_grounding.retrieval.models import ChunkRecord, Hit, ScoredHit


def scored(chunk_id, document_id, extent_id, score, specificity):
    chunk = ChunkRecord(
        chunk_id=chunk_id, document_id=document_id, ordinal=0, text_original="o", text_en="e",
        heading_path="", anchor=None, extent_id=extent_id, authority=Authority.OFFICIAL_INFO,
        categories=(), url="u", identifier=None, title_original="t", title_en="t",
        language="de", valid_from=None, retrieved_at=datetime(2026, 1, 1), license=None,
        source_id="s",
    )
    hit = Hit(chunk=chunk, rrf_score=0.0, dense_rank=None, lexical_rank=None)
    return ScoredHit(hit=hit, score=score, specificity=specificity, category_overlap=0, authority_score=0)


def test_caps_chunks_per_document():
    items = (
        scored(1, 100, "CH", 0.9, 0.25), scored(2, 100, "CH", 0.8, 0.25),
        scored(3, 100, "CH", 0.7, 0.25), scored(4, 200, "CH", 0.6, 0.25),
    )
    out = diversify(items, limit=3, per_document_cap=2)
    assert [s.hit.chunk.chunk_id for s in out] == [1, 2, 4]


def test_guarantees_most_specific_extent_present():
    items = (
        scored(1, 100, "CH", 0.9, 0.25), scored(2, 200, "CH", 0.8, 0.25),
        scored(3, 300, "CH-ZH-261-K3", 0.1, 1.0),
    )
    out = diversify(items, limit=2, per_document_cap=2)
    ids = [s.hit.chunk.chunk_id for s in out]
    assert 3 in ids and len(ids) == 2


def test_empty_input():
    assert diversify((), limit=5, per_document_cap=2) == ()
