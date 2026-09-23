from datetime import UTC, date, datetime

import pytest

from swiss_grounding.corpus.calendar import OPENERZ_SOURCE, calendar_document
from swiss_grounding.corpus.persist import persist_document, upsert_source
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration


def test_calendar_document_persists_as_municipal_chunks(corpus_db):
    doc = calendar_document(8003, [{"date": "2026-09-17", "waste_type": "cardboard", "zip": 8003}],
                             today=date(2026, 9, 10))
    with connect(corpus_db) as conn:
        upsert_source(conn, OPENERZ_SOURCE)
        assert persist_document(conn, doc, OPENERZ_SOURCE, datetime(2026, 9, 10, tzinfo=UTC)) == "added"
        row = conn.execute("select extent_id, text from corpus.chunk").fetchone()
    assert row["extent_id"] == "CH-ZH-261" and "17.09.2026" in row["text"]
