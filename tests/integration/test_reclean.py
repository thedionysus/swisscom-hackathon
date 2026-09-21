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
        # document_change is not named here: CASCADE still empties it, because it has a
        # foreign key onto document, but it is no longer truncated up front as a table this
        # suite treats as always-empty -- tests that need a document_change row insert one
        # themselves, after this fixture runs, so reclean is exercised against real rows.
        conn.execute("truncate chunk, document restart identity cascade")
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


def test_reclean_drops_document_referenced_by_document_change(url):
    # Every crawled document gets a document_change row (ingest/persist.py); document_change
    # has no ON DELETE CASCADE onto document (db/schema.sql), so reclean must clear the rows
    # that reference a document it drops -- as either document_id or previous_document_id --
    # or the DELETE FROM document raises ForeignKeyViolation and the whole transaction (all
    # 80 chunk deletions included) rolls back.
    with connect(url) as conn:
        doc = conn.execute(
            "update chunk set heading_path = 'Navigation' where document_id = "
            "(select id from document where source_id = 'ch_ch' and url = 'https://www.ch.ch/en/dogs') "
            "returning document_id"
        ).fetchone()
        sibling = conn.execute(
            "select id from document where source_id = 'ch_ch' and url = 'https://www.ch.ch/en/dogs/basel-stadt'"
        ).fetchone()
        conn.execute(
            "insert into document_change (run_id, document_id, change_type) values (%s, %s, %s)",
            ("test-run", doc["document_id"], "added"),
        )
        conn.execute(
            "insert into document_change (run_id, document_id, previous_document_id, change_type) "
            "values (%s, %s, %s, %s)",
            ("test-run", sibling["id"], doc["document_id"], "modified"),
        )

    with connect(url) as conn:
        report = reclean_all(conn)
        document_gone = conn.execute(
            "select id from document where id = %s", (doc["document_id"],)
        ).fetchone()
        change_rows_left = conn.execute(
            "select id from document_change where document_id = %s or previous_document_id = %s",
            (doc["document_id"], doc["document_id"]),
        ).fetchall()

    assert document_gone is None
    assert change_rows_left == []
    ch = next(s for s in report.by_source if s.source_id == "ch_ch")
    assert ch.dropped_documents == 1


def test_reclean_nulls_superseded_by_pointing_at_a_dropped_document(url):
    # document.superseded_by is a self-referencing FK with no ON DELETE CASCADE either; the
    # live data has no case of it today, but the fix must not leave a dangling pointer.
    with connect(url) as conn:
        doc = conn.execute(
            "update chunk set heading_path = 'Navigation' where document_id = "
            "(select id from document where source_id = 'ch_ch' and url = 'https://www.ch.ch/en/dogs') "
            "returning document_id"
        ).fetchone()
        old_version = conn.execute(
            """
            insert into document (source_id, url, title_original, title_en, language, extent_id,
                                  authority, content_hash, version, status, superseded_by)
            values ('ch_ch', 'https://www.ch.ch/en/dogs-old', 'Dogs (old)', 'Dogs (old)', 'en', 'CH',
                    'official_info', 'test-superseded-hash', 1, 'superseded', %s)
            returning id
            """,
            (doc["document_id"],),
        ).fetchone()

    with connect(url) as conn:
        reclean_all(conn)
        refreshed = conn.execute(
            "select superseded_by from document where id = %s", (old_version["id"],)
        ).fetchone()

    assert refreshed["superseded_by"] is None


def test_reclean_second_run_drops_nothing(url):
    with connect(url) as conn:
        doc = conn.execute("select id from document where source_id = 'zh_ch'").fetchone()
        _insert_navigation_chunk(conn, doc["id"])

    with connect(url) as conn:
        reclean_all(conn)
        report = reclean_all(conn)

    assert report.by_source == ()
    assert report.dropped_chunks == 0
