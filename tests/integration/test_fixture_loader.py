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
FIXTURE = Path(__file__).parent.parent / "fixtures" / "zurich_hiking.json"


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
    return u


def test_load_fixture_inserts_documents_and_chunks(url):
    with connect(url) as conn:
        report = load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
        docs = conn.execute("select count(*) as n from document").fetchone()["n"]
        chunks = conn.execute("select count(*) as n from chunk").fetchone()["n"]
        sample = conn.execute(
            "select extent_id, authority, categories, document_status from chunk limit 1"
        ).fetchone()
    assert report.documents == 8
    assert report.chunks == 8
    assert docs == 8 and chunks == 8
    assert sample["document_status"] == "current"


def test_load_fixture_twice_is_idempotent(url):
    with connect(url) as conn:
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
        docs = conn.execute("select count(*) as n from document").fetchone()["n"]
    assert docs == 8


def test_fixture_with_unknown_source_fails_clearly(url, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"documents":[{"source_id":"nope","url":"u","title_original":"t","title_en":"t","language":"de","extent_id":"CH","authority":"official_info","categories":[],"chunks":[]}]}')
    with connect(url) as conn, pytest.raises(ValueError, match="unknown source"):
        load_fixture(conn, bad, FakeEmbedder(dim=8))
