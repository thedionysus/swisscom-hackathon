"""Loads the structural probe corpus.

The corpus mirrors the live database: cantonal pages sit at canton level after re-narrowing,
and the waste calendar carries a trailing window of past events as well as upcoming ones.
"""
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

pytestmark = pytest.mark.integration
CORPUS = Path(__file__).parent.parent / "fixtures" / "probe_corpus.json"


def test_probe_corpus_loads_and_covers_every_level():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        report = load_fixture(conn, CORPUS, FakeEmbedder(dim=8))
        extents = {r["extent_id"] for r in conn.execute("select distinct extent_id from document").fetchall()}
        events = conn.execute("select count(*) from document where event_date is not null").fetchone()["count"]
    assert report.documents == 16
    assert {"CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3", "CH-BS"} <= extents
    assert events == 5
