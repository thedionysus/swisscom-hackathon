import os
from pathlib import Path

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder
from swiss_grounding.retrieval.search import hybrid_search

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parent.parent / "fixtures" / "zurich_hiking.json"


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
    return u


def test_search_filters_by_extent_path(url):
    embedder = FakeEmbedder(dim=8)
    with connect(url) as conn:
        hits = hybrid_search(
            conn, embedder, question="Do I need to leash my dog?",
            extent_path=("CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3"), as_of=None, top_n=50,
        )
    extents = {h.chunk.extent_id for h in hits}
    assert "CH-BS" not in extents
    assert {"CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3"} >= extents
    assert len(hits) >= 5


def test_search_country_only_returns_only_ch(url):
    with connect(url) as conn:
        hits = hybrid_search(
            conn, FakeEmbedder(dim=8), question="leash dog hiking",
            extent_path=("CH",), as_of=None, top_n=50,
        )
    assert {h.chunk.extent_id for h in hits} == {"CH"}


def test_search_as_of_excludes_future_valid_from(url):
    from datetime import date

    with connect(url) as conn:
        hits = hybrid_search(
            conn, FakeEmbedder(dim=8), question="animal welfare",
            extent_path=("CH",), as_of=date(2000, 1, 1), top_n=50,
        )
    identifiers = {h.chunk.identifier for h in hits}
    assert "SR 455 Art. 6" not in identifiers       # valid_from 2008
    assert "SR 704 Art. 1" in identifiers           # valid_from 1987


def test_hit_carries_document_fields(url):
    with connect(url) as conn:
        hits = hybrid_search(conn, FakeEmbedder(dim=8), question="dog", extent_path=("CH",), as_of=None, top_n=5)
    h = hits[0]
    assert h.chunk.url.startswith("https://")
    assert h.chunk.title_en
    assert h.chunk.retrieved_at is not None
