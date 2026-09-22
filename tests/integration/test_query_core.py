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


def test_ambiguous_location_message_names_the_cantons(core):
    resp = core.query(QueryRequest(question="dog rules", location="Wil"))
    assert resp.status == "needs_location"
    assert "Zurich" in resp.message
    assert "St. Gallen" in resp.message


# The two tests below state a topic where they previously stated none. Topic is a hard
# filter now (ADR 0003), so a request carrying none falls through to the local classifier
# — whose floor and margin are calibrated against bge-m3 (`topics.py`) and mean nothing
# under the 8-dimension FakeEmbedder this suite runs on, where it picks a category out of
# hash collisions. Both tests are about extent scoping, not about topics, so they pin the
# topic their own question is plainly about rather than letting a meaningless classifier
# decide what they retrieve. `test_topic_filter.py` covers the no-topic case at the level
# where the classifier is not in the way.
def test_country_question_returns_only_country_scoped(core):
    resp = core.query(QueryRequest(question="Who is responsible for hiking trails?",
                                   location="Switzerland", topics=("hiking",)))
    assert resp.status == "results"
    assert {c.extent_id for c in resp.citations} == {"CH"}


def test_unindexed_canton_falls_back_to_federal_only(core):
    resp = core.query(QueryRequest(question="dog leash", location="Genève"))
    assert resp.status == "results"
    assert resp.resolved_location_id == "CH-GE-6621"  # city of Geneva; the canton is the alternative reading
    assert {c.extent_id for c in resp.citations} == {"CH"}


def test_no_evidence_when_nothing_indexed_for_path(core):
    with connect(core.database_url) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
    resp = core.query(QueryRequest(question="dog leash", location="Genève"))
    assert resp.status == "no_evidence"
    assert resp.resolved_location_id == "CH-GE-6621"  # city of Geneva; the canton is the alternative reading
    assert "Genève" in resp.message  # the register carries the German-language label


def test_location_in_question_is_detected(core):
    resp = core.query(QueryRequest(question="What are the dog rules in Basel?", topics=("dogs",)))
    assert resp.status == "results"
    assert resp.resolved_location_id == "CH-BS-2701"  # city of Basel; the canton is the alternative reading
    assert all(c.extent_id in {"CH", "CH-BS"} for c in resp.citations)


def test_empty_question_is_invalid_request(core):
    resp = core.query(QueryRequest(question="   ", location="Wiedikon"))
    assert resp.status == "invalid_request"
    assert resp.field == "question"
    assert resp.citations == ()


def test_unknown_categories_are_invalid_request(core):
    resp = core.query(QueryRequest(question="dog rules", location="Wiedikon", categories=("nope",)))
    assert resp.status == "invalid_request"
    assert resp.field == "categories"
    assert "nope" in resp.message


def test_unknown_topics_are_invalid_request_not_a_silent_empty_result(core):
    """An unknown topic matches no chunk, so without this it would surface as an
    unexplained `no_evidence` and the caller would never see the typo."""
    resp = core.query(QueryRequest(question="dog rules", location="Wiedikon", topics=("dgos",)))
    assert resp.status == "invalid_request"
    assert resp.field == "topics"
    assert "dgos" in resp.message


def test_limit_above_maximum_is_clamped_not_rejected(core):
    resp = core.query(QueryRequest(question="dog leash", location="Wiedikon", limit=999))
    assert resp.status == "results"
    assert resp.field is None


def test_limit_below_minimum_is_clamped_not_rejected(core):
    resp = core.query(QueryRequest(question="dog leash", location="Wiedikon", limit=0))
    assert resp.status == "results"
    assert len(resp.citations) == 1
