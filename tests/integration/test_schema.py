import os

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema

pytestmark = pytest.mark.integration

EXPECTED_TABLES = {
    "location", "source", "source_suggestion", "document", "chunk", "document_change", "fetch_state",
}


def test_schema_creates_tables():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        rows = conn.execute(
            "select table_name from information_schema.tables where table_schema='public'"
        ).fetchall()
    names = {r["table_name"] for r in rows}
    assert EXPECTED_TABLES <= names


CHECK_CONSTRAINTS_SQL = """
select rel.relname as table_name, pg_get_constraintdef(con.oid) as definition
from pg_constraint con join pg_class rel on rel.oid = con.conrelid
where con.contype = 'c' and rel.relname in ('document', 'chunk')
"""


def _check_definitions():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        rows = conn.execute(CHECK_CONSTRAINTS_SQL).fetchall()
    return [(r["table_name"], r["definition"]) for r in rows]


def test_chunk_document_status_is_constrained():
    defs = _check_definitions()
    assert any(
        table == "chunk" and "document_status" in d and "pending_enrichment" in d
        for table, d in defs
    ), defs


def test_authority_is_constrained_on_document_and_chunk():
    defs = _check_definitions()
    for table in ("document", "chunk"):
        assert any(
            t == table and "authority" in d and "federal_law" in d and "institutional" in d
            for t, d in defs
        ), (table, defs)
