"""`chunk.context_en` and the `tsv` column that must be rebuilt over it.

`db init` applies `schema.sql` wholesale and leans on `create table if not exists`, which
silently skips an existing table. Editing the inline `tsv` definition therefore changes a
fresh database and leaves a live one on the old definition -- a half-migration in which
search quietly ignores every generated description. These tests pin both halves: a fresh
database gets the new definition, and a database still carrying the old one is rebuilt.
"""

import os

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources

pytestmark = pytest.mark.integration

DIM = 8
OLD_TSV_DEFINITION = "to_tsvector('english'::regconfig, text_en)"

GENERATED_EXPRESSION = """
select pg_get_expr(ad.adbin, ad.adrelid) as definition
from pg_attribute a
join pg_attrdef ad on ad.adrelid = a.attrelid and ad.adnum = a.attnum
where a.attrelid = 'chunk'::regclass and a.attname = 'tsv' and a.attgenerated = 's'
"""
COLUMN = """
select is_nullable, column_default
from information_schema.columns
where table_name = 'chunk' and column_name = 'context_en'
"""
INDEX = "select 1 as present from pg_indexes where tablename = 'chunk' and indexname = 'chunk_tsv_idx'"


def _tsv_definition(conn) -> str | None:
    row = conn.execute(GENERATED_EXPRESSION).fetchone()
    return row["definition"] if row else None


@pytest.fixture
def url() -> str:
    """The session database is shared, so this seeds the real registry rather than inventing a
    source of its own: a stray `source` row would still be there for every later test."""
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=DIM)
    with connect(u) as conn:
        conn.execute("truncate chunk, document_change, document, fetch_state restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
    return u


def _a_chunk(conn, context_en: str, text_en: str) -> int:
    document_id = conn.execute(
        """
        insert into document (source_id, url, title_original, title_en, language, extent_id,
                              authority, content_hash)
        values ('fedlex', 'https://x/' || gen_random_uuid(), 't', 't', 'de', 'CH', 'federal_law', 'h')
        returning id
        """
    ).fetchone()["id"]
    return conn.execute(
        """
        insert into chunk (document_id, ordinal, text_original, text_en, context_en, embedding,
                           chunk_hash, extent_id, authority)
        values (%s, 0, 'o', %s, %s, %s, 'h', 'CH', 'federal_law') returning id
        """,
        (document_id, text_en, context_en, [0.0] * DIM),
    ).fetchone()["id"]


def test_chunk_carries_context_that_defaults_to_empty(url):
    """`not null default ''` is what makes concatenating context and text safe everywhere."""
    with connect(url) as conn:
        row = conn.execute(COLUMN).fetchone()
    assert row is not None, "chunk.context_en does not exist"
    assert row["is_nullable"] == "NO" and row["column_default"].startswith("''")


def test_the_keyword_index_sees_the_generated_context(url):
    with connect(url) as conn:
        chunk_id = _a_chunk(conn, context_en="From the Animal Welfare Act", text_en="Anyone who intentionally")
        hits = conn.execute(
            "select tsv @@ to_tsquery('english', %s) as hit from chunk where id = %s",
            ("welfare", chunk_id),
        ).fetchone()
    assert hits["hit"] is True


def test_the_boundary_word_of_each_half_survives_the_join(url):
    """Without a separator the last word of the context fuses with the first of the text."""
    with connect(url) as conn:
        chunk_id = _a_chunk(conn, context_en="Sets penalties", text_en="Anyone who intentionally")
        row = conn.execute(
            """
            select tsv @@ to_tsquery('english', 'penalties') as context_word,
                   tsv @@ to_tsquery('english', 'anyone') as text_word
            from chunk where id = %s
            """,
            (chunk_id,),
        ).fetchone()
    assert (row["context_word"], row["text_word"]) == (True, True)


def test_an_empty_context_leaves_the_text_indexed_as_before(url):
    with connect(url) as conn:
        chunk_id = _a_chunk(conn, context_en="", text_en="Anyone who intentionally")
        row = conn.execute(
            "select tsv @@ to_tsquery('english', 'anyone') as hit from chunk where id = %s", (chunk_id,)
        ).fetchone()
    assert row["hit"] is True


def test_a_second_application_changes_nothing(url):
    with connect(url) as conn:
        first = _tsv_definition(conn)
    apply_schema(url, embedding_dim=DIM)
    with connect(url) as conn:
        second = _tsv_definition(conn)
        index = conn.execute(INDEX).fetchone()
    assert first is not None and "context_en" in first
    assert second == first
    assert index is not None, "chunk_tsv_idx was lost"


def test_a_database_still_holding_the_old_definition_is_rebuilt(url):
    """The live database's `chunk` table already exists, so `create table if not exists` skips it.
    Only the guarded block can carry it forward, and dropping `tsv` takes `chunk_tsv_idx` with it."""
    with connect(url) as conn:
        conn.execute("alter table chunk drop column tsv")
        conn.execute(
            f"alter table chunk add column tsv tsvector generated always as ({OLD_TSV_DEFINITION}) stored"
        )
        assert conn.execute(INDEX).fetchone() is None, "dropping tsv should have dropped its index"
    apply_schema(url, embedding_dim=DIM)
    with connect(url) as conn:
        definition = _tsv_definition(conn)
        index = conn.execute(INDEX).fetchone()
    assert definition is not None and "context_en" in definition
    assert index is not None, "chunk_tsv_idx was not recreated"
