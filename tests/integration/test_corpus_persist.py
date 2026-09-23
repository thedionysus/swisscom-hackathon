from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from swiss_grounding.corpus.models import ParsedDocument, ParsedSection, SourceSpec
from swiss_grounding.corpus.persist import (
    group_id,
    known_state,
    persist_document,
    promote_due,
    quarantine,
    touch_unchanged,
    upsert_source,
    withdraw,
)
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration
NOW = datetime(2026, 9, 24, 8, tzinfo=UTC)
SPEC = SourceSpec(id="fedlex", name="Fedlex", publisher="Federal Chancellery", authority="federal_law",
                  level="federal", extent_id="CH", connector="fedlex", tier=1, languages=("de",),
                  config={"sr_numbers": ["220"]})
HTML_SPEC = SourceSpec(id="bern", name="Bern", publisher="Stadt Bern", authority="official_info",
                       level="municipal", extent_id="CH-BE-351", connector="html", tier=1, languages=("de",))
ABSTRACT = "https://fedlex.data.admin.ch/eli/cc/27/317_321_377"


def _doc(url, text="1 Nach Ablauf der Probezeit.", status="current", valid_from=date(2025, 7, 1), lang="de"):
    section = ParsedSection("art_336_c", ("SR 220 OR", "Art. 336c"), "art_336_c", text)
    return ParsedDocument(source_id="fedlex", url=url, language=lang, work_key=ABSTRACT, title="Obligationenrecht",
                          sections=(section,), identifier="SR 220", valid_from=valid_from, status=status)


def _page(url, work_key="html:https://x/", text="Inhalt der Seite."):
    return ParsedDocument(source_id="bern", url=url, language="de", work_key=work_key, title="Seite",
                          sections=(ParsedSection("de:0", ("Seite",), None, text),))


def _scan(url, digest):
    page = ParsedSection("de:p1", ("Merkblatt", "p. 1"), "page=1", "", needs_ocr=True,
                         ocr_image="/artifacts/p1.png", ocr_digest=digest)
    return ParsedDocument(source_id="bern", url=url, language="de", work_key=f"html:{url}", title="Merkblatt",
                          sections=(page,), extraction="pdf_text")


def _rows(conn):
    return conn.execute("select url, status, superseded_by, valid_to from corpus.document order by id").fetchall()


def test_new_document_writes_chunks_with_prior_topics(corpus_db):
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        assert persist_document(conn, _doc("u1"), SPEC, NOW) == "added"
        chunk = conn.execute("select * from corpus.chunk").fetchone()
    assert chunk["language"] == "de" and chunk["align_key"] == "art_336_c"
    assert chunk["topics"] == ["work"]
    assert chunk["translation_group_id"] == group_id(ABSTRACT)
    assert chunk["status"] == "current" and chunk["extent_id"] == "CH" and chunk["authority"] == "federal_law"


def test_new_version_reuses_descriptions_of_unchanged_chunks(corpus_db):
    """RAG review E3: a refresh pays only for chunks whose text changed."""
    unchanged = ParsedSection("art_1", ("SR 220 OR", "Art. 1"), "art_1", "Zum Abschlusse eines Vertrages.")
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        old = _doc("u2024", valid_from=date(2024, 1, 1))
        persist_document(conn, replace(old, sections=(unchanged, *old.sections)), SPEC, NOW)
        conn.execute("update corpus.chunk set description = 'Vertragsabschluss', topics = '{business}' "
                     "where align_key = 'art_1'")
        conn.execute("update corpus.chunk set description = 'Kündigungsschutz' where align_key = 'art_336_c'")
        new = _doc("u2025", valid_from=date(2025, 7, 1), text="1 Geänderter Text.")
        persist_document(conn, replace(new, sections=(unchanged, *new.sections)), SPEC, NOW)
        rows = {r["align_key"]: r for r in conn.execute(
            "select align_key, description, topics from corpus.chunk where status = 'current'").fetchall()}
    assert rows["art_1"]["description"] == "Vertragsabschluss" and rows["art_1"]["topics"] == ["business"]
    assert rows["art_336_c"]["description"] == ""          # changed text is described again


def test_ocr_chunk_hash_follows_the_page_image(corpus_db):
    """A rescanned page with a new image is described again even though its text is still empty."""
    with connect(corpus_db) as conn:
        upsert_source(conn, HTML_SPEC)
        persist_document(conn, _scan("https://x/m.pdf", "img-v1"), HTML_SPEC, NOW)
        first = conn.execute("select chunk_hash from corpus.chunk").fetchone()["chunk_hash"]
        conn.execute("update corpus.chunk set description = 'Merkblatt Abfall'")
        assert persist_document(conn, _scan("https://x/m.pdf", "img-v2"), HTML_SPEC, NOW) == "modified"
        current = conn.execute("select chunk_hash, description from corpus.chunk where status = 'current'").fetchone()
    assert current["chunk_hash"] != first
    assert current["description"] == ""


def test_same_content_is_unchanged(corpus_db):
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        persist_document(conn, _doc("u1"), SPEC, NOW)
        assert persist_document(conn, _doc("u1"), SPEC, NOW) == "unchanged"
        assert len(_rows(conn)) == 1


def test_changed_content_at_same_url_supersedes(corpus_db):
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        persist_document(conn, _doc("u1"), SPEC, NOW)
        assert persist_document(conn, _doc("u1", text="1 Neu."), SPEC, NOW) == "modified"
        rows = _rows(conn)
    assert [r["status"] for r in rows] == ["superseded", "current"]
    assert rows[0]["superseded_by"] is not None


def test_new_consolidation_retires_the_old_one(corpus_db):
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        persist_document(conn, _doc("u2024", valid_from=date(2024, 1, 1)), SPEC, NOW)
        persist_document(conn, _doc("u2025", valid_from=date(2025, 7, 1), text="1 Neu."), SPEC, NOW)
        rows = _rows(conn)
        stale = conn.execute("select count(*) as n from corpus.chunk where status = 'current'").fetchone()["n"]
    assert [r["status"] for r in rows] == ["superseded", "current"]
    assert rows[0]["valid_to"] == date(2025, 7, 1)
    assert stale == 1


def test_undated_documents_sharing_a_group_both_stay_current(corpus_db):
    """Amendment A1: rule 3 applies only to dated consolidations; HTML pages are versioned by URL."""
    with connect(corpus_db) as conn:
        upsert_source(conn, HTML_SPEC)
        assert persist_document(conn, _page("https://x/a"), HTML_SPEC, NOW) == "added"
        assert persist_document(conn, _page("https://x/b", text="Andere Seite."), HTML_SPEC, NOW) == "added"
        rows = _rows(conn)
        chunks = conn.execute("select count(*) as n from corpus.chunk where status = 'current'").fetchone()["n"]
    assert [r["status"] for r in rows] == ["current", "current"]
    assert [r["superseded_by"] for r in rows] == [None, None]
    assert chunks == 2


def test_scheduled_version_coexists_then_takes_over(corpus_db):
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        persist_document(conn, _doc("now"), SPEC, NOW)
        persist_document(conn, _doc("later", status="scheduled", valid_from=date(2027, 1, 1), text="1 Neu."), SPEC, NOW)
        assert [r["status"] for r in _rows(conn)] == ["current", "scheduled"]
        persist_document(conn, _doc("later", status="current", valid_from=date(2027, 1, 1), text="1 Neu."), SPEC, NOW)
        assert [r["status"] for r in _rows(conn)] == ["superseded", "current"]


def test_promote_due_makes_scheduled_versions_current_on_their_date(corpus_db):
    """Amendment A5: a scheduled consolidation takes over without being re-emitted by the connector."""
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        persist_document(conn, _doc("now"), SPEC, NOW)
        later = _doc("later", status="scheduled", valid_from=date(2027, 1, 1), text="1 Neu.")
        extra = ParsedSection("art_1", ("SR 220 OR", "Art. 1"), "art_1", "Fussnote.")
        persist_document(conn, replace(later, sections=(*later.sections, extra)), SPEC, NOW)
        conn.execute("update corpus.chunk set status = 'boilerplate' where align_key = 'art_1'")
        assert promote_due(conn, date(2026, 12, 31)) == 0
        assert [r["status"] for r in _rows(conn)] == ["current", "scheduled"]
        assert promote_due(conn, date(2027, 1, 1)) == 1
        rows = _rows(conn)
        chunks = {r["align_key"]: r["status"] for r in conn.execute(
            "select c.align_key, c.status from corpus.chunk c join corpus.document d on d.id = c.document_id "
            "where d.url = 'later'").fetchall()}
        old_chunks = conn.execute("select c.status from corpus.chunk c join corpus.document d "
                                  "on d.id = c.document_id where d.url = 'now'").fetchall()
    assert [r["status"] for r in rows] == ["superseded", "current"]
    assert rows[0]["valid_to"] == date(2027, 1, 1) and rows[0]["superseded_by"] is not None
    assert chunks == {"art_336_c": "current", "art_1": "boilerplate"}
    assert [r["status"] for r in old_chunks] == ["superseded"]


def test_languages_of_one_act_share_a_group_and_do_not_supersede_each_other(corpus_db):
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        persist_document(conn, _doc("de"), SPEC, NOW)
        persist_document(conn, _doc("fr", lang="fr", text="1 Après le temps d'essai."), SPEC, NOW)
        groups = conn.execute("select distinct translation_group_id from corpus.document").fetchall()
        statuses = [r["status"] for r in _rows(conn)]
    assert len(groups) == 1 and statuses == ["current", "current"]


def test_fetch_state_touch_withdraw_and_quarantine(corpus_db):
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        persist_document(conn, _doc("u1"), SPEC, NOW)
        assert "u1" in known_state(conn, "fedlex")
        touch_unchanged(conn, "u1", NOW)
        withdraw(conn, "u1")
        assert _rows(conn)[0]["status"] == "withdrawn"
        quarantine(conn, "fedlex", "u9", "fetch", "HTTP 500")
        quarantine(conn, "fedlex", "u9", "fetch", "HTTP 503")
        q = conn.execute("select attempts, reason from corpus.quarantine").fetchone()
    assert q["attempts"] == 2 and q["reason"] == "HTTP 503"
