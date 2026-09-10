from datetime import date, datetime

from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.cite import build_citation
from swiss_grounding.retrieval.models import ChunkRecord, Hit, ScoredHit


def test_citation_copies_fields_and_labels_extent():
    chunk = ChunkRecord(
        chunk_id=7, document_id=3, ordinal=0, text_original="Im Kanton Zürich gilt Leinenpflicht.",
        text_en="In the Canton of Zurich dogs must be leashed.", heading_path="Leinenpflicht",
        anchor="leinenpflicht", extent_id="CH-ZH", authority=Authority.OFFICIAL_INFO,
        categories=("dogs",), url="https://www.zh.ch/x", identifier=None,
        title_original="Hunde", title_en="Dogs", language="de", valid_from=date(2020, 1, 1),
        retrieved_at=datetime(2026, 9, 1), license="zh terms", source_id="zh_ch",
    )
    sh = ScoredHit(hit=Hit(chunk=chunk, rrf_score=0.0, dense_rank=1, lexical_rank=None),
                   score=0.7, specificity=0.5, category_overlap=1.0, authority_score=0.6)
    tree = LocationTree.from_locations(seed_locations())
    c = build_citation(sh, tree)
    assert c.url == "https://www.zh.ch/x" and c.anchor == "leinenpflicht"
    assert c.extent_label == "Zurich" and c.extent_id == "CH-ZH"
    assert c.authority == "official_info"
    assert c.snippet_original.startswith("Im Kanton")
    assert c.score == 0.7
    assert c.license == "zh terms"
