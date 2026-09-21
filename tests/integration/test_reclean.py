import os
from pathlib import Path

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.ingest.reclean import SourceReclean, reclean_all
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parent.parent / "fixtures" / "zurich_hiking.json"
DOGS_URL = "https://www.ch.ch/en/dogs"
BASEL_URL = "https://www.ch.ch/en/dogs/basel-stadt"


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        # document_change is not named here, but cascade empties it too, the same as
        # test_renarrow.py: it has a foreign key onto document.
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


def _make_only_chunk_boilerplate(conn) -> int:
    """Flip the sole real chunk of the ch_ch 'dogs' document to Navigation; returns its document id.
    ch_ch has two documents in the fixture (dogs and Basel-Stadt); this touches only the former,
    leaving the latter -- see _sibling_document_id -- a real, untouched document."""
    row = conn.execute(
        "update chunk set heading_path = 'Navigation' where document_id = "
        "(select id from document where source_id = 'ch_ch' and url = %s) "
        "returning document_id",
        (DOGS_URL,),
    ).fetchone()
    return row["document_id"]


def _sibling_document_id(conn) -> int:
    """The id of ch_ch's Basel-Stadt document, untouched by _make_only_chunk_boilerplate."""
    return conn.execute(
        "select id from document where source_id = 'ch_ch' and url = %s", (BASEL_URL,)
    ).fetchone()["id"]


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
    with connect(url) as conn:
        dropped_id = _make_only_chunk_boilerplate(conn)
        sibling_id = _sibling_document_id(conn)

    with connect(url) as conn:
        report = reclean_all(conn)
        document_gone = conn.execute("select id from document where id = %s", (dropped_id,)).fetchone()
        sibling_still_present = conn.execute(
            "select id from document where id = %s", (sibling_id,)
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
        dropped_id = _make_only_chunk_boilerplate(conn)
        sibling_id = _sibling_document_id(conn)
        conn.execute(
            "insert into document_change (run_id, document_id, change_type) values (%s, %s, %s)",
            ("test-run", dropped_id, "added"),
        )
        conn.execute(
            "insert into document_change (run_id, document_id, previous_document_id, change_type) "
            "values (%s, %s, %s, %s)",
            ("test-run", sibling_id, dropped_id, "modified"),
        )

    with connect(url) as conn:
        report = reclean_all(conn)
        document_gone = conn.execute("select id from document where id = %s", (dropped_id,)).fetchone()
        change_rows_left = conn.execute(
            "select id from document_change where document_id = %s or previous_document_id = %s",
            (dropped_id, dropped_id),
        ).fetchall()

    assert document_gone is None
    assert change_rows_left == []
    ch = next(s for s in report.by_source if s.source_id == "ch_ch")
    assert ch.dropped_documents == 1


def test_reclean_nulls_previous_document_id_on_a_surviving_documents_change_row(url):
    # A document_change row can belong to a document that survives reclean while its
    # previous_document_id points at the earlier version reclean drops. reclean's licence is
    # to erase the history *of the documents it drops*, not to punch holes in the history of
    # documents it keeps -- so the row must survive with the dangling pointer nulled, not be
    # deleted outright the way a row whose own document_id is dropped is.
    with connect(url) as conn:
        dropped_id = _make_only_chunk_boilerplate(conn)
        sibling_id = _sibling_document_id(conn)
        change_row = conn.execute(
            "insert into document_change (run_id, document_id, previous_document_id, change_type) "
            "values (%s, %s, %s, %s) returning id",
            ("test-run", sibling_id, dropped_id, "modified"),
        ).fetchone()

    with connect(url) as conn:
        reclean_all(conn)
        document_gone = conn.execute("select id from document where id = %s", (dropped_id,)).fetchone()
        surviving_row = conn.execute(
            "select document_id, previous_document_id from document_change where id = %s",
            (change_row["id"],),
        ).fetchone()

    assert document_gone is None
    assert surviving_row is not None
    assert surviving_row["document_id"] == sibling_id
    assert surviving_row["previous_document_id"] is None


def test_reclean_nulls_superseded_by_pointing_at_a_dropped_document(url):
    # document.superseded_by is a self-referencing FK with no ON DELETE CASCADE either; the
    # live data has no case of it today, but the fix must not leave a dangling pointer.
    with connect(url) as conn:
        dropped_id = _make_only_chunk_boilerplate(conn)
        old_version = conn.execute(
            """
            insert into document (source_id, url, title_original, title_en, language, extent_id,
                                  authority, content_hash, version, status, superseded_by)
            values ('ch_ch', 'https://www.ch.ch/en/dogs-old', 'Dogs (old)', 'Dogs (old)', 'en', 'CH',
                    'official_info', 'test-superseded-hash', 1, 'superseded', %s)
            returning id
            """,
            (dropped_id,),
        ).fetchone()

    with connect(url) as conn:
        reclean_all(conn)
        refreshed = conn.execute(
            "select superseded_by from document where id = %s", (old_version["id"],)
        ).fetchone()

    assert refreshed["superseded_by"] is None


def test_reclean_by_source_spans_multiple_sources(url):
    with connect(url) as conn:
        zh_doc = conn.execute("select id from document where source_id = 'zh_ch'").fetchone()
        _insert_navigation_chunk(conn, zh_doc["id"])
        _make_only_chunk_boilerplate(conn)

    with connect(url) as conn:
        report = reclean_all(conn)

    assert report.by_source == (
        SourceReclean(source_id="ch_ch", dropped_chunks=1, dropped_documents=1),
        SourceReclean(source_id="zh_ch", dropped_chunks=1, dropped_documents=0),
    )
    assert report.dropped_chunks == 2
    assert report.dropped_documents == 1


def test_reclean_report_examined_counts_every_chunk_seen(url):
    with connect(url) as conn:
        total_chunks_before = conn.execute("select count(*) as n from chunk").fetchone()["n"]
        report = reclean_all(conn)

    assert report.examined == total_chunks_before


def test_reclean_dry_run_reports_without_mutating(url):
    with connect(url) as conn:
        zh_doc = conn.execute("select id from document where source_id = 'zh_ch'").fetchone()
        _insert_navigation_chunk(conn, zh_doc["id"])
        dropped_id = _make_only_chunk_boilerplate(conn)
        chunk_count_before = conn.execute("select count(*) as n from chunk").fetchone()["n"]

    with connect(url) as conn:
        report = reclean_all(conn, dry_run=True)

    with connect(url) as conn:
        chunk_count_after = conn.execute("select count(*) as n from chunk").fetchone()["n"]
        dropped_document_still_present = conn.execute(
            "select id from document where id = %s", (dropped_id,)
        ).fetchone()

    assert chunk_count_after == chunk_count_before
    assert dropped_document_still_present is not None
    assert report.by_source == (
        SourceReclean(source_id="ch_ch", dropped_chunks=1, dropped_documents=1),
        SourceReclean(source_id="zh_ch", dropped_chunks=1, dropped_documents=0),
    )


def test_reclean_second_run_drops_nothing(url):
    with connect(url) as conn:
        doc = conn.execute("select id from document where source_id = 'zh_ch'").fetchone()
        _insert_navigation_chunk(conn, doc["id"])

    with connect(url) as conn:
        reclean_all(conn)
        report = reclean_all(conn)

    assert report.by_source == ()
    assert report.dropped_chunks == 0
