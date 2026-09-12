import os

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema

pytestmark = pytest.mark.integration

EMBEDDING_TYPE_SQL = """
select format_type(atttypid, atttypmod) as type from pg_attribute
where attrelid = 'chunk'::regclass and attname = 'embedding'
"""


def test_suite_database_is_isolated_from_the_quick_start_database():
    # The quick-start `db init` creates chunk.embedding as vector(EMBEDDING_DIM), 1024 by default.
    # The suite must run against its own database so that its 8-dim schema is what actually exists.
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        row = conn.execute(EMBEDDING_TYPE_SQL).fetchone()
    assert row["type"] == "vector(8)", row
