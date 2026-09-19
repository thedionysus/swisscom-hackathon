import os
from pathlib import Path

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.ingest.renarrow import renarrow_all
from swiss_grounding.locations.repository import load_tree, upsert_locations
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
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
        conn.execute("update document set extent_id = 'CH-ZH-261' where source_id = 'zh_ch'")
        conn.execute(
            "update chunk set extent_id = 'CH-ZH-261' where document_id in "
            "(select id from document where source_id = 'zh_ch')"
        )
    return u


def test_renarrow_moves_document_and_chunks_back_to_source_default(url):
    with connect(url) as conn:
        tree = load_tree(conn)
        report = renarrow_all(conn, tree)
        doc = conn.execute(
            "select extent_id, extent_reason from document where source_id = 'zh_ch'"
        ).fetchone()
        chunk = conn.execute(
            "select extent_id from chunk where document_id in "
            "(select id from document where source_id = 'zh_ch')"
        ).fetchone()
    assert report.moved == 1
    assert doc["extent_id"] == "CH-ZH"
    assert doc["extent_reason"] == "source_default"
    assert chunk["extent_id"] == "CH-ZH"


def test_renarrow_second_run_moves_nothing(url):
    with connect(url) as conn:
        tree = load_tree(conn)
        renarrow_all(conn, tree)
        report = renarrow_all(conn, tree)
    assert report.moved == 0
