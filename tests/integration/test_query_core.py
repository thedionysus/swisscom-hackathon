import os
from pathlib import Path

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.locations.repository import load_tree, upsert_locations
from swiss_grounding.locations.resolver import LocationResolver
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder
from swiss_grounding.retrieval.models import QueryRequest
from swiss_grounding.retrieval.query_core import QueryCore
from swiss_grounding.retrieval.rerank import RerankWeights

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parent.parent / "fixtures" / "zurich_hiking.json"


class NoGeo:
    def search_communes(self, text):
        return ()


@pytest.fixture
def core():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
        tree = load_tree(conn)
    return QueryCore(
        database_url=url, tree=tree, resolver=LocationResolver(tree, NoGeo()),
        embedder=FakeEmbedder(dim=8), weights=RerankWeights(),
    )


def test_neighborhood_question_prefers_specific_and_excludes_siblings(core):
    resp = core.query(QueryRequest(question="Where can my dog run off leash?", location="Wiedikon", categories=("dogs",)))
    assert resp.status == "results"
    assert resp.resolved_location_id == "CH-ZH-261-K3-ALT-WIEDIKON"
    extents = [c.extent_id for c in resp.citations]
    assert extents[0] == "CH-ZH-261-K3"
    assert "CH-BS" not in extents
    assert any(e == "CH-ZH-261" for e in extents)


def test_missing_location_returns_needs_location(core):
    resp = core.query(QueryRequest(question="Do I need to leash my dog in the forest?"))
    assert resp.status == "needs_location"
    assert resp.citations == ()
    assert "city, canton, or postal code" in resp.message


def test_unresolvable_location_returns_needs_location_with_reason(core):
    resp = core.query(QueryRequest(question="dog rules", location="Atlantis"))
    assert resp.status == "needs_location"
    assert "Atlantis" in resp.message


def test_country_question_returns_only_country_scoped(core):
    resp = core.query(QueryRequest(question="Who is responsible for hiking trails?", location="Switzerland"))
    assert resp.status == "results"
    assert {c.extent_id for c in resp.citations} == {"CH"}


def test_unindexed_canton_falls_back_to_federal_only(core):
    resp = core.query(QueryRequest(question="dog leash", location="Genève"))
    assert resp.status == "results"
    assert resp.resolved_location_id == "CH-GE"
    assert {c.extent_id for c in resp.citations} == {"CH"}


def test_no_evidence_when_nothing_indexed_for_path(core):
    with connect(core.database_url) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
    resp = core.query(QueryRequest(question="dog leash", location="Genève"))
    assert resp.status == "no_evidence"
    assert resp.resolved_location_id == "CH-GE"
    assert "Geneva" in resp.message


def test_location_in_question_is_detected(core):
    resp = core.query(QueryRequest(question="What are the dog rules in Basel?"))
    assert resp.status == "results"
    assert resp.resolved_location_id == "CH-BS"
    assert all(c.extent_id in {"CH", "CH-BS"} for c in resp.citations)
