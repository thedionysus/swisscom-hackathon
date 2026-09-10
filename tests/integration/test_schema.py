import os

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema

pytestmark = pytest.mark.integration

EXPECTED_TABLES = {
    "location", "source", "source_suggestion", "document", "chunk", "document_change",
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
