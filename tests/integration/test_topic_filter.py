"""Topic is a hard filter on retrieval, and an on-topic empty result.

These run against a dedicated fixture rather than the live corpus on purpose. The live
index still carries its old per-document tags -- 563 fedlex chunks assert `dogs, hiking,
safety, transport, waste` simultaneously -- so a hard topic filter would appear to
filter almost nothing there, and a test written against it would assert today's bad
tags rather than the behaviour under test. `tests/fixtures/topic_filter.json`
states that behaviour instead: one extent path carrying documents on two different
topics, one document carrying no topic at all, and no document anywhere carrying
`schools`.
"""

import os
from datetime import date
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
from swiss_grounding.retrieval.search import hybrid_search

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parent.parent / "fixtures" / "topic_filter.json"
EMBEDDING_DIM = 8
# Before the fixture's single calendar event, so it ranks as upcoming rather than past.
FROZEN_TODAY = date(2026, 9, 16)


class NoGeo:
    """8003 resolves from the postal-code register alone; nothing here needs GeoAdmin."""

    def search_communes(self, text):
        return ()


@pytest.fixture
def core():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=EMBEDDING_DIM)
    with connect(url) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=EMBEDDING_DIM))
        tree = load_tree(conn)
    return QueryCore(
        database_url=url, tree=tree, resolver=LocationResolver(tree, NoGeo()),
        embedder=FakeEmbedder(dim=EMBEDDING_DIM), weights=RerankWeights(),
        today=lambda: FROZEN_TODAY,
    )


def test_a_chunk_without_the_topic_is_not_returned(core):
    """The plan's first test. Without the filter the Wiedikon dog zone and the untagged
    district-office page sit on the same path and come back alongside the cardboard
    pages, because every chunk on the path clears the extent filter."""
    resp = core.query(QueryRequest(question="When is cardboard collected?",
                                   location="8003", topics=("waste",)))
    assert resp.status == "results"
    assert resp.citations
    assert all("waste" in c.categories for c in resp.citations)


def test_no_evidence_when_nothing_on_the_path_carries_the_topic(core):
    """The plan's second test. The place is covered; the subject is not."""
    resp = core.query(QueryRequest(question="Which schools are nearby?",
                                   location="8003", topics=("schools",)))
    assert resp.status == "no_evidence"
    assert "schools" in resp.message
    assert resp.coverage  # the coverage signal still reports what IS there


def test_the_two_no_evidence_causes_do_not_share_a_message(core):
    """One cause is a place with no documents; the other is a place with
    documents but none on topic. A calling model must be able to act differently on
    each -- ask about another place versus ask about another subject -- so neither
    message may be reachable for the other cause."""
    on_topic_gap = core.query(QueryRequest(question="Which schools are nearby?",
                                           location="8003", topics=("schools",)))
    with connect(core.database_url) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
    place_gap = core.query(QueryRequest(question="Which schools are nearby?",
                                        location="8003", topics=("schools",)))

    assert on_topic_gap.status == place_gap.status == "no_evidence"
    assert on_topic_gap.message != place_gap.message
    # The uncovered place must not be blamed on the topic: the topic never got a chance.
    assert "schools" not in place_gap.message
    assert place_gap.resolved_location_label in place_gap.message


def test_caller_supplied_topics_win_over_the_soft_category_hint(core):
    """The caller supplies the topic. `topics` is the new, explicit field;
    `categories` is the older hint the same caller may still be sending. When both
    arrive, the explicit one decides what is filtered on."""
    resp = core.query(QueryRequest(question="When is cardboard collected?", location="8003",
                                   topics=("waste",), categories=("dogs",)))
    assert resp.status == "results"
    assert all("waste" in c.categories for c in resp.citations)
    assert resp.categories_used == ("waste",)


def test_categories_used_reports_the_constraint_that_was_applied(core):
    resp = core.query(QueryRequest(question="Where can my dog run off leash?",
                                   location="8003", topics=("dogs", "waste")))
    assert resp.categories_used == ("dogs", "waste")


def test_coverage_is_unaffected_by_the_topic_filter(core):
    """Coverage is about places, not topics: it counts what is indexed for each extent
    on the path, and a topic the corpus never mentions must not make a covered place
    look uncovered."""
    covered = core.query(QueryRequest(question="When is cardboard collected?",
                                      location="8003", topics=("waste",)))
    off_topic = core.query(QueryRequest(question="Which schools are nearby?",
                                        location="8003", topics=("schools",)))
    assert covered.coverage == off_topic.coverage
    assert any(row.documents > 0 for row in off_topic.coverage)


def test_a_question_the_classifier_declines_still_returns_everything_on_the_path(core):
    """The end-to-end link between `resolve_topics` returning `()` and the SQL applying
    no filter at all. It is the one path in this file that can break silently: change
    `search.py` to send `list(topics)` rather than null for an empty tuple, or have
    `resolve_topics` substitute some default, and this question returns nothing while
    every other test here -- all of which state a topic -- stays green.

    No stub and no real embedder are needed: FakeEmbedder at dim 8 puts this
    question below TOPIC_FLOOR, so the classifier genuinely declines. The
    `categories_used` assertion is a precondition rather than decoration -- if the
    classifier ever starts having an opinion about this question, this test must fail
    loudly instead of quietly testing nothing.
    """
    resp = core.query(QueryRequest(question="When is cardboard collected?", location="8003"))
    assert resp.categories_used == ()      # precondition: no topic constraint was applied
    assert resp.status == "results"
    # The untagged chunk surviving is the proof. Any non-empty filter excludes it, so a
    # filter on nothing would have left this response empty.
    assert any(c.categories == () for c in resp.citations)


# The three tests below go through `hybrid_search` rather than `QueryCore.query`. They
# pin specific topic values -- one topic, several, none -- and the classifier in front of
# `QueryCore.query` cannot be made to produce them: its thresholds are calibrated against
# bge-m3 (see `topics.py`) and under the 8-dimension FakeEmbedder this suite runs on it
# answers out of hash collisions. The test above covers the one case the classifier does
# reach honestly here, so the whole path is checked end to end as well.
# what they are about is the filter itself and `QueryCore.query` would put the topic
# classifier in front of it. The classifier's thresholds are calibrated against bge-m3
# (see `topics.py`); under the 8-dimension FakeEmbedder this suite must use, they are
# meaningless, and a test that ran the classifier here would be asserting hash collisions
# rather than behaviour.


def test_no_topics_retrieves_every_topic_and_the_untagged_chunk(core):
    """`()` means no constraint. If it filtered on nothing instead, a question the
    classifier declines to place would return zero results rather than degrading to
    search on the extent path alone."""
    with connect(core.database_url) as conn:
        hits = hybrid_search(
            conn, FakeEmbedder(dim=EMBEDDING_DIM), question="collection day",
            extent_path=("CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3"), as_of=None, topics=(),
        )
    found = {h.chunk.title_en: h.chunk.categories for h in hits}
    assert found["District office 3"] == ()          # carries no topic at all
    assert found["Dog zone Wiedikon"] == ("dogs",)   # carries a different topic
    assert found["Cardboard"] == ("waste",)


def test_any_topic_filter_hides_the_chunk_that_carries_no_topic(core):
    """The cost of a hard filter, accepted deliberately: a chunk
    the re-tagging pass named no topic for does not carry this one either, so it is not
    evidence. This is why `()` may not be spelled as an empty array in the SQL."""
    with connect(core.database_url) as conn:
        hits = hybrid_search(
            conn, FakeEmbedder(dim=EMBEDDING_DIM), question="collection day",
            extent_path=("CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3"), as_of=None,
            topics=("waste",),
        )
    assert {h.chunk.title_en for h in hits} == {
        "Environmental Protection Act", "Waste and raw materials", "Cardboard",
        "Waste collection cardboard in 8003 on 2026-09-24",
    }


def test_a_chunk_qualifies_by_any_one_of_the_topics_not_all(core):
    """`&&` is overlap, not containment. The classifier returns a margin band because a
    near-tie is not evidence for its top entry alone, so a band must widen what is
    retrievable rather than narrow it to chunks carrying the whole band."""
    with connect(core.database_url) as conn:
        hits = hybrid_search(
            conn, FakeEmbedder(dim=EMBEDDING_DIM), question="collection day",
            extent_path=("CH", "CH-ZH-261-K3"), as_of=None, topics=("dogs", "waste"),
        )
    assert {h.chunk.title_en for h in hits} == {
        "Animal Welfare Ordinance", "Environmental Protection Act",
        "Dog zone Wiedikon", "Waste collection cardboard in 8003 on 2026-09-24",
    }
