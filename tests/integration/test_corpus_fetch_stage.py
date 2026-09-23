from datetime import UTC, date, datetime

import pytest

from swiss_grounding.corpus.fetch_stage import run_fetch
from swiss_grounding.corpus.models import (
    ConnectorResult,
    DiscoveredPdf,
    ParsedDocument,
    ParsedSection,
    SourceSpec,
)
from swiss_grounding.corpus.persist import persist_document, upsert_source
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration
NOW = datetime(2026, 9, 24, tzinfo=UTC)


def _spec(sid, connector="html"):
    return SourceSpec(id=sid, name=sid, publisher=sid, authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector=connector, tier=1, languages=("de",),
                      config={"start_urls": ["https://x/"], "allow_prefixes": ["https://x/"]})


def _doc(sid, url, language="de"):
    return ParsedDocument(source_id=sid, url=url, language=language, work_key=f"html:{url}", title="T",
                          sections=(ParsedSection("de:0", ("T",), None, "Inhalt der Seite."),))


class FakeHtml:
    def run(self, spec, known):
        if spec.id == "boom":
            raise RuntimeError("site exploded")
        return ConnectorResult(documents=(_doc(spec.id, f"https://x/{spec.id}"),),
                               errors=((f"https://x/{spec.id}/bad", "HTTP 500"),),
                               pdfs=(DiscoveredPdf("https://x/a.pdf", "de", "A", spec.id),))


class FakePdf:
    def run_pdfs(self, spec, pdfs, known):
        return ConnectorResult(documents=tuple(_doc(spec.id, p.url) for p in pdfs))


class OneBadDocument:
    """The middle document violates the language check, so its insert fails inside the savepoint."""

    def run(self, spec, known):
        return ConnectorResult(documents=(_doc(spec.id, "https://x/first"),
                                          _doc(spec.id, "https://x/broken", language="xx"),
                                          _doc(spec.id, "https://x/last")))


class NothingNew:
    def run(self, spec, known):
        return ConnectorResult()


def test_runs_sources_persists_and_quarantines(corpus_db):
    report = run_fetch(corpus_db, [_spec("bern"), _spec("boom")], {"html": FakeHtml()}, FakePdf(),
                       now=lambda: NOW, workers=2)
    with connect(corpus_db) as conn:
        urls = {r["url"] for r in conn.execute("select url from corpus.document").fetchall()}
        q = {(r["url"], r["stage"]) for r in conn.execute("select url, stage from corpus.quarantine").fetchall()}
    assert urls == {"https://x/bern", "https://x/a.pdf"}
    assert ("https://x/bern/bad", "fetch") in q
    assert ("source:boom", "fetch") in q
    assert report["bern"]["added"] == 2
    assert report["boom"]["failed"] == 1


def test_failed_document_is_quarantined_without_losing_its_neighbours(corpus_db):
    report = run_fetch(corpus_db, [_spec("bern")], {"html": OneBadDocument()}, None, now=lambda: NOW)
    with connect(corpus_db) as conn:
        urls = {r["url"] for r in conn.execute("select url from corpus.document").fetchall()}
        q = conn.execute("select url, stage from corpus.quarantine").fetchall()
    assert urls == {"https://x/first", "https://x/last"}
    assert [(r["url"], r["stage"]) for r in q] == [("https://x/broken", "persist")]
    assert report["bern"]["added"] == 2 and report["bern"]["failed"] == 1


def test_scheduled_versions_are_promoted_after_the_run(corpus_db):
    """Amendment A5: the connector reports nothing new, yet the due scheduled version takes over."""
    fedlex = SourceSpec(id="fedlex", name="Fedlex", publisher="BK", authority="federal_law", level="federal",
                        extent_id="CH", connector="fedlex", tier=1, languages=("de",))
    section = ParsedSection("art_1", ("SR 220", "Art. 1"), "art_1", "Text.")
    old = ParsedDocument(source_id="fedlex", url="u2025", language="de", work_key="eli/cc/27", title="OR",
                         sections=(section,), valid_from=date(2025, 1, 1))
    new = ParsedDocument(source_id="fedlex", url="u2026", language="de", work_key="eli/cc/27", title="OR",
                         sections=(ParsedSection("art_1", ("SR 220", "Art. 1"), "art_1", "Neu."),),
                         valid_from=date(2026, 9, 1), status="scheduled")
    with connect(corpus_db) as conn:
        upsert_source(conn, fedlex)
        persist_document(conn, old, fedlex, datetime(2026, 8, 1, tzinfo=UTC))
        persist_document(conn, new, fedlex, datetime(2026, 8, 1, tzinfo=UTC))
    run_fetch(corpus_db, [fedlex], {"fedlex": NothingNew()}, None, now=lambda: NOW)
    with connect(corpus_db) as conn:
        rows = conn.execute("select url, status, valid_to from corpus.document order by id").fetchall()
    assert [(r["url"], r["status"]) for r in rows] == [("u2025", "superseded"), ("u2026", "current")]
    assert rows[0]["valid_to"] == date(2026, 9, 1)
