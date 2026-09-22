"""The clock QueryCore reranks against. Nothing here is about topics.

What `as_of` means to retrieval -- the boundary it is refused against and where that
check sits relative to location resolution -- is `test_query_core_as_of.py`. This file
is only about which date the reranker is handed.

Every request below states `topics` even so, because a request that states none falls
through to the local classifier (ADR 0004), which needs a real embedder -- and these
build QueryCore with `embedder=None` on purpose, having monkeypatched away the only
thing that used to touch it. The value matches the fixture chunk's own category so the
hard topic filter is a no-op for what these assert.
"""
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

    class Cursor:
        def fetchall(self): return []

    class Conn:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, *a, **k): return Cursor()

    seen = {}
    def fake_rerank(hits, tree_, node, cats, weights, today=date.today):
        seen["today"] = today()
        return ()
    monkeypatch.setattr(query_core, "connect", lambda url: Conn())
    monkeypatch.setattr(query_core, "hybrid_search", lambda *a, **k: (Hit(chunk=chunk, rrf_score=1.0, dense_rank=1, lexical_rank=1),))
    monkeypatch.setattr(query_core, "rerank", fake_rerank)
    core = QueryCore(database_url="x", tree=tree, resolver=Resolver(), embedder=None, weights=RerankWeights(),
                     today=lambda: date(2026, 9, 16))
    core.query(QueryRequest(question="q", location="Switzerland", topics=("waste",)))
    assert seen["today"] == date(2026, 9, 16)


def test_as_of_replaces_today_for_the_reranker(monkeypatch):
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

    class Cursor:
        def fetchall(self): return []
        # A dated request now asks the index for the earliest version it can answer for
        # before it searches (D2). 1985 is well before either date under test here, so
        # both are answerable and this test still exercises only the clock.
        def fetchone(self): return {"earliest": date(1985, 1, 1)}

    class Conn:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, *a, **k): return Cursor()

    seen = {}
    def fake_rerank(hits, tree_, node, cats, weights, today=date.today):
        seen["today"] = today()
        return ()
    monkeypatch.setattr(query_core, "connect", lambda url: Conn())
    monkeypatch.setattr(query_core, "hybrid_search", lambda *a, **k: (Hit(chunk=chunk, rrf_score=1.0, dense_rank=1, lexical_rank=1),))
    monkeypatch.setattr(query_core, "rerank", fake_rerank)
    core = QueryCore(database_url="x", tree=tree, resolver=Resolver(), embedder=None, weights=RerankWeights(),
                     today=lambda: date(2026, 9, 16))

    core.query(QueryRequest(question="q", location="Switzerland", topics=("waste",),
                            as_of=date(2026, 9, 8)))
    assert seen["today"] == date(2026, 9, 8)

    core.query(QueryRequest(question="q", location="Switzerland", topics=("waste",)))
    assert seen["today"] == date(2026, 9, 16)
