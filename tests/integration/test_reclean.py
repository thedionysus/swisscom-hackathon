import os
from pathlib import Path

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.ingest.reclean import reclean_all
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
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
    return u


def _insert_navigation_chunk(conn, document_id: int) -> None:
    """Add a Navigation chunk to an already-real document, mirroring the live corpus where
    boilerplate and content chunks share a document."""
    embedding = FakeEmbedder(dim=8).embed(["Read page aloud  Environment and Energy"])[0]
    conn.execute(
        """
        insert into chunk (document_id, ordinal, text_original, text_en, heading_path, anchor, embedding,
                           chunk_hash, extent_id, authority, categories)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (document_id, 99, "Navigation", "Read page aloud  Environment and Energy", "Navigation", None,
         embedding, "test-navigation-chunk", "CH-ZH", "official_info", []),
    )


def test_reclean_drops_navigation_chunk_and_keeps_real_chunk(url):
    with connect(url) as conn:
        doc = conn.execute("select id from document where source_id = 'zh_ch'").fetchone()
        _insert_navigation_chunk(conn, doc["id"])

    with connect(url) as conn:
        report = reclean_all(conn)
        remaining = conn.execute(
            "select heading_path from chunk where document_id = %s", (doc["id"],)
        ).fetchall()
        document_still_present = conn.execute(
            "select id from document where id = %s", (doc["id"],)
        ).fetchone()

    assert {r["heading_path"] for r in remaining} == {"Leinenpflicht"}
    assert document_still_present is not None
    zh = next(s for s in report.by_source if s.source_id == "zh_ch")
    assert zh.dropped_chunks == 1
    assert zh.dropped_documents == 0
    assert report.dropped_chunks == 1
    assert report.dropped_documents == 0


def test_reclean_drops_document_left_with_no_chunks(url):
    # ch_ch has two documents in the fixture; only the one whose sole chunk turns boilerplate
    # should be dropped, leaving the sibling document (and its own real chunk) untouched.
    with connect(url) as conn:
        doc = conn.execute(
            "update chunk set heading_path = 'Navigation' where document_id = "
            "(select id from document where source_id = 'ch_ch' and url = 'https://www.ch.ch/en/dogs') "
            "returning document_id"
        ).fetchone()
        sibling = conn.execute(
            "select id from document where source_id = 'ch_ch' and url = 'https://www.ch.ch/en/dogs/basel-stadt'"
        ).fetchone()

    with connect(url) as conn:
        report = reclean_all(conn)
        document_gone = conn.execute(
            "select id from document where id = %s", (doc["document_id"],)
        ).fetchone()
        sibling_still_present = conn.execute(
            "select id from document where id = %s", (sibling["id"],)
        ).fetchone()

    assert document_gone is None
    assert sibling_still_present is not None
    ch = next(s for s in report.by_source if s.source_id == "ch_ch")
    assert ch.dropped_chunks == 1
    assert ch.dropped_documents == 1


def test_reclean_second_run_drops_nothing(url):
    with connect(url) as conn:
        doc = conn.execute("select id from document where source_id = 'zh_ch'").fetchone()
        _insert_navigation_chunk(conn, doc["id"])

    with connect(url) as conn:
        reclean_all(conn)
        report = reclean_all(conn)

    assert report.by_source == ()
    assert report.dropped_chunks == 0
