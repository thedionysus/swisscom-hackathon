"""What text actually reaches the embedder, end to end through `QueryCore`.

`tests/unit/test_query_text.py` pins how the three text fields compose. This pins that
the composed string is the one the running query uses -- the join could be perfect and
`query_core` could still hand `request.question` to the dense arm, and every unit test
would stay green.

The embedder is a recorder wrapped around `FakeEmbedder`, so the assertions are about
*which strings were embedded*, never about which chunk came back. Under the 8-dimension
FakeEmbedder this suite must use, a ranking assertion would be asserting a hash collision
(`tests/integration/test_topic_filter.py` records where that has bitten before).
"""

import os
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import numpy as np
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
FIXTURE = Path(__file__).parent.parent / "fixtures" / "topic_filter.json"
EMBEDDING_DIM = 8
FROZEN_TODAY = date(2026, 9, 16)

QUESTION_DE = "Wann wird das Altpapier abgeholt?"
QUESTION_EN = "When is waste paper collected?"
TOPIC_EN = "household waste and recycling collection days"


class RecordingEmbedder:
    """A FakeEmbedder that remembers every text it was asked to embed.

    Deliberately not a subclass: the recording is the point, and wrapping keeps the
    fake's vector behaviour identical to the one every other test in this suite sees.
    """

    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim
        self._inner = FakeEmbedder(dim=dim)
        self.texts: list[str] = []

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]:
        self.texts.extend(texts)
        return self._inner.embed(texts)


class NoGeo:
    """8003 resolves from the postal-code register alone; nothing here needs GeoAdmin."""

    def search_communes(self, text):
        return ()


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=EMBEDDING_DIM)
    with connect(u) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=EMBEDDING_DIM))
    return u


@pytest.fixture
def make_core(url):
    def build(embedder):
        with connect(url) as conn:
            tree = load_tree(conn)
        return QueryCore(
            database_url=url, tree=tree, resolver=LocationResolver(tree, NoGeo()),
            embedder=embedder, weights=RerankWeights(), today=lambda: FROZEN_TODAY,
        )

    return build


def test_the_running_query_embeds_the_english_question_and_the_topic(make_core):
    embedder = RecordingEmbedder()
    resp = make_core(embedder).query(QueryRequest(
        question=QUESTION_DE, question_en=QUESTION_EN, topic_en=TOPIC_EN,
        location="8003", topics=("waste",),
    ))
    assert resp.status == "results"
    assert embedder.texts == [f"{QUESTION_EN} {TOPIC_EN}"]
    assert resp.query_fields == ("question_en", "topic_en")


def test_the_verbatim_question_is_never_embedded_when_english_was_supplied(make_core):
    """Neither by the dense arm nor by the topic classifier. This is the whole point of
    the contract: the English index is never asked to match a German vector when the caller
    has already paid for the translation."""
    embedder = RecordingEmbedder()
    make_core(embedder).query(QueryRequest(
        question=QUESTION_DE, question_en=QUESTION_EN, topic_en=TOPIC_EN, location="8003",
    ))
    assert embedder.texts, "nothing was embedded, so nothing was actually checked"
    assert QUESTION_DE not in embedder.texts


def test_an_un_updated_client_still_searches_on_the_verbatim_question(make_core):
    """The degrade path for a client that sends no English, and the response says it degraded."""
    embedder = RecordingEmbedder()
    resp = make_core(embedder).query(QueryRequest(
        question=QUESTION_DE, location="8003", topics=("waste",),
    ))
    assert resp.status == "results"
    assert embedder.texts == [QUESTION_DE]
    assert resp.query_fields == ("question",)


def test_the_response_names_who_decided_the_topic(make_core):
    core = make_core(RecordingEmbedder())
    stated = core.query(QueryRequest(question=QUESTION_DE, location="8003", topics=("waste",)))
    deprecated = core.query(QueryRequest(question=QUESTION_DE, location="8003", categories=("waste",)))
    guessed = core.query(QueryRequest(question=QUESTION_DE, location="8003"))

    assert stated.topic_decided_by == "topics"
    assert deprecated.topic_decided_by == "categories"
    assert guessed.topic_decided_by == "classifier"
    # The deprecated field is an alias, not a second meaning: it filters identically.
    assert deprecated.categories_used == stated.categories_used == ("waste",)


def test_a_refused_request_reports_no_query_at_all(make_core):
    """`query_fields` is empty when no query was built, so an empty tuple can never be
    misread as "the verbatim question was used"."""
    resp = make_core(RecordingEmbedder()).query(
        QueryRequest(question="   ", location="8003", topics=("waste",))
    )
    assert resp.status == "invalid_request"
    assert resp.query_fields == ()
    assert resp.topic_decided_by == ""
