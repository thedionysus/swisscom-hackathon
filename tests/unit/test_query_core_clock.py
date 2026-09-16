from dataclasses import fields
from datetime import date

from swiss_grounding.retrieval.query_core import QueryCore


def test_query_core_has_today_field_defaulting_to_date_today():
    names = {f.name: f for f in fields(QueryCore)}
    assert "today" in names
    assert names["today"].default == date.today


def test_query_passes_injected_today_to_rerank(monkeypatch):
    from datetime import UTC, datetime

    from swiss_grounding.locations.models import Level, Location, ResolvedLocation
    from swiss_grounding.locations.tree import LocationTree
    from swiss_grounding.registry.models import Authority
    from swiss_grounding.retrieval import query_core
    from swiss_grounding.retrieval.models import ChunkRecord, Hit, QueryRequest
    from swiss_grounding.retrieval.rerank import RerankWeights

    tree = LocationTree.from_locations([Location(id="CH", parent_id=None, level=Level.COUNTRY, bfs_id=None,
                                                  lindas_uri=None, names={"en": "Switzerland"}, aliases=())])
    chunk = ChunkRecord(chunk_id=1, document_id=1, ordinal=0, text_original="t", text_en="t", heading_path="",
                        anchor=None, extent_id="CH", authority=Authority.OFFICIAL_INFO, categories=("waste",),
                        url="https://x", identifier=None, title_original="t", title_en="t", language="en",
                        valid_from=None, retrieved_at=datetime(2026, 9, 14, tzinfo=UTC), license=None,
                        source_id="open_erz", event_date=date(2026, 9, 10))

    class Resolver:
        def resolve(self, text):
            return ResolvedLocation(location=tree.get("CH"), path=("CH",), method="alias", input_text=text)

    class Conn:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    seen = {}
    def fake_rerank(hits, tree_, node, cats, weights, today=date.today):
        seen["today"] = today()
        return ()
    monkeypatch.setattr(query_core, "connect", lambda url: Conn())
    monkeypatch.setattr(query_core, "hybrid_search", lambda *a, **k: (Hit(chunk=chunk, rrf_score=1.0, dense_rank=1, lexical_rank=1),))
    monkeypatch.setattr(query_core, "rerank", fake_rerank)
    core = QueryCore(database_url="x", tree=tree, resolver=Resolver(), embedder=None, weights=RerankWeights(),
                     today=lambda: date(2026, 9, 16))
    core.query(QueryRequest(question="q", location="Switzerland"))
    assert seen["today"] == date(2026, 9, 16)
