"""persist_document's unchanged path, against a stand-in connection (the full behaviour is covered by
tests/integration/test_corpus_persist.py, which needs a database)."""
from datetime import UTC, datetime

from swiss_grounding.corpus.models import ParsedDocument, ParsedSection, SourceSpec, content_hash
from swiss_grounding.corpus.persist import persist_document

NOW = datetime(2026, 9, 25, 8, tzinfo=UTC)
SPEC = SourceSpec(id="bern", name="Bern", publisher="Stadt Bern", authority="official_info", level="municipal",
                  extent_id="CH-BE-351", connector="html", tier=1, languages=("de",))
DOC = ParsedDocument(source_id="bern", url="https://x/p", language="de", work_key="html:https://x/p", title="Seite",
                     sections=(ParsedSection("de:0", ("Seite",), None, "Inhalt der Seite."),),
                     artifact_path="data/raw/bern/aa-bb.html")


class _Rows:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _Conn:
    """Answers the live-row lookup with a row holding the same content hash; records every statement."""

    def __init__(self):
        self.statements: list[tuple[str, tuple]] = []

    def execute(self, sql, params=()):
        self.statements.append((sql, params))
        if sql.startswith("select id, content_hash"):
            return _Rows({"id": 7, "content_hash": content_hash(DOC), "status": "current", "source_id": "bern",
                          "valid_from": None})
        return _Rows(None)


def test_an_unchanged_document_points_at_the_artifact_this_fetch_wrote():
    """#12: a re-fetch of the same text may write its file under a name the row never had."""
    conn = _Conn()
    assert persist_document(conn, DOC, SPEC, NOW) == "unchanged"
    touched = [params for sql, params in conn.statements if sql.startswith("update corpus.document set last_seen_at")]
    assert touched == [(NOW, "data/raw/bern/aa-bb.html", 7)]
