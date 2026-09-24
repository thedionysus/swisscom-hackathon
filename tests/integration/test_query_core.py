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


def test_neighborhood_question_leads_with_the_nearest_specific_evidence(core):
    """Tier ordering changed what "prefers specific" means, and this test changed with it.

    It used to assert that the district chunk (`CH-ZH-261-K3`) led, because specificity
    was a term in a single score and the most specific extent always won it. Ordering is
    now `(tier, -score)`, and a chunk only claims a tier when its cosine distance clears
    `RerankWeights.relevance_floor`. On this fixture the district chunk sits at 0.9197
    against a floor of 0.55 and the city chunk at 0.4969, so the city chunk leads and the
    district chunk is demoted -- which is the intended case: a weak local chunk
    does not leapfrog but is still returned.

    The sibling-exclusion half is untouched, and the assertions below are deliberately
    stronger than the ones they replace: they pin the *mechanism* (the leader claimed a
    tier, the demoted chunk did not) rather than only the resulting order, and they hold
    the district chunk to being present, which is the guarantee the floor must never
    break.
    """
    resp = core.query(QueryRequest(question="Where can my dog run off leash?", location="Wiedikon", categories=("dogs",)))
    assert resp.status == "results"
    assert resp.resolved_location_id == "CH-ZH-261-K3-ALT-WIEDIKON"
    extents = [c.extent_id for c in resp.citations]
    assert extents[0] == "CH-ZH-261"
    assert resp.citations[0].tier is not None
    assert "CH-BS" not in extents
    assert "CH-ZH-261-K3" in extents                                    # demoted, not dropped
    district = next(c for c in resp.citations if c.extent_id == "CH-ZH-261-K3")
    assert district.tier is None and district.distance > RerankWeights().relevance_floor


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
# filter now, so a request carrying none falls through to the local classifier
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


def test_as_of_before_the_earliest_indexed_version_is_refused(core):
    """The `as_of` refusal, end to end. The fixture's oldest `valid_from` is 1987, so 1900
    reaches nothing; the old behaviour searched anyway and returned the undated pages that
    bypassed the date filter as the answer to a question about 1900."""
    from datetime import date

    resp = core.query(QueryRequest(question="dog leash", location="Zürich",
                                   categories=("dogs",), as_of=date(1900, 1, 1)))
    assert resp.status == "invalid_request"
    assert resp.field == "as_of"
    assert "1987-01-01" in resp.message
    assert resp.citations == ()


def test_a_topic_wipeout_reads_the_same_dated_and_undated(core):
    """THE CRITICAL DEFECT, end to end on the corpus the reviewer used. No document on the
    Zurich path carries `waste`, so the topic is the sole cause of the empty result. The
    previous routing blamed any dated empty result on the date, so the server stated the
    topic was uncovered when asked undated and stated the opposite one query later."""
    from datetime import date

    undated = core.query(QueryRequest(question="cardboard collection", location="Zürich",
                                      topics=("waste",)))
    dated = core.query(QueryRequest(question="cardboard collection", location="Zürich",
                                    topics=("waste",), as_of=date(2020, 1, 1)))
    assert undated.status == dated.status == "no_evidence"
    assert "waste" in undated.message
    assert undated.message == dated.message


def test_a_dated_query_on_documents_that_hold_no_chunks_is_not_blamed_on_the_date(core):
    """The second half of the same defect: with the chunks gone the documents remain, so
    `coverage_rows` still calls the path covered, and the date got nothing to exclude."""
    from datetime import date

    with connect(core.database_url) as conn:
        conn.execute("delete from chunk")

    resp = core.query(QueryRequest(question="dog leash", location="Zürich",
                                   topics=("dogs",), as_of=date(2020, 1, 1)))
    assert resp.status == "no_evidence"
    assert "2020-01-01" not in resp.message
    assert "dogs" not in resp.message
    assert any(row.documents for row in resp.coverage)   # coverage still says covered


def _only_basel_is_dated(core):
    """The live shape: the queried path records no validity date anywhere, while a
    document off the path keeps the global boundary reachable so the request is not
    refused before it reaches retrieval."""
    from datetime import date

    with connect(core.database_url) as conn:
        conn.execute("update document set valid_from = null where extent_id <> 'CH-BS'")
        conn.execute("update document set valid_from = date '1987-01-01' "
                     "where extent_id = 'CH-BS'")
    return date(2020, 1, 1)


def test_a_genuine_date_wipeout_is_reported_as_one(core):
    """The date really is the sole cause here: on-topic chunks are indexed on the path and
    every one of them is excluded for recording no validity date."""
    as_of = _only_basel_is_dated(core)

    resp = core.query(QueryRequest(question="dog leash", location="Zurich",
                                   topics=("dogs",), as_of=as_of))
    assert resp.status == "no_evidence"
    assert "2020-01-01" in resp.message
    assert "dogs" in resp.message
    # Nothing on this path records a date, so "try another as_of" would be false.
    assert "no as_of can be answered" in resp.message
    assert "none of them carry the topic" not in resp.message
    assert any(row.documents for row in resp.coverage)   # coverage still says covered


def test_a_date_wipeout_names_the_boundary_when_the_path_has_one(core):
    """And when the path does record a date, the message is as actionable as the refusal
    is: it hands back the date, not "a different as_of may help"."""
    as_of = _only_basel_is_dated(core)
    with connect(core.database_url) as conn:
        conn.execute("update document set valid_from = date '2022-06-01' "
                     "where extent_id = 'CH-ZH-261'")

    resp = core.query(QueryRequest(question="dog leash", location="Zurich",
                                   topics=("dogs",), as_of=as_of))
    assert resp.status == "no_evidence"
    assert "2022-06-01" in resp.message   # after the as_of, so the date excluded it
