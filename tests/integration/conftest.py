"""Integration test session setup.

The suite provisions its own throwaway database on the server named by DATABASE_URL
and points DATABASE_URL at it for the whole session. This keeps the 8-dimension test
schema from colliding with a quick-start database created by `db init` (vector(1024)),
and leaves the developer's demo data untouched. It also forces the fake LLM and
embedding backends so a developer's .env with real API keys never leaks into tests.
"""

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest

TEST_DB_PREFIX = "swiss_grounding_test_"
# Environment variables override .env, so the suite never uses a developer's real backends.
FAKE_BACKENDS = {
    "LLM_BACKEND": "fake",
    "EMBEDDING_BACKEND": "fake",
    "EMBEDDING_DIM": "8",
    "CORPUS_LLM_PROVIDER": "fake",
    "CORPUS_INDEXES": "bge-m3",
    "QUERY_EMBEDDER": "fake",
    "RERANKER_MODEL": "overlap",
}


def pytest_collection_modifyitems(config, items):
    if os.environ.get("DATABASE_URL"):
        return
    skip = pytest.mark.skip(reason="DATABASE_URL not set; integration tests skipped")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


def _admin_connection(url: str) -> psycopg.Connection:
    return psycopg.connect(url, autocommit=True)


def _test_database_url(base_url: str, name: str) -> str:
    return str(psycopg.conninfo.make_conninfo(base_url, dbname=name))


@pytest.fixture(scope="session", autouse=True)
def isolated_database_url() -> Iterator[str | None]:
    base_url = os.environ.get("DATABASE_URL")
    if not base_url:
        yield None
        return
    name = f"{TEST_DB_PREFIX}{uuid.uuid4().hex[:8]}"
    with _admin_connection(base_url) as admin:
        admin.execute(f'create database "{name}"')
    test_url = _test_database_url(base_url, name)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DATABASE_URL", test_url)
        for key, value in FAKE_BACKENDS.items():
            patch.setenv(key, value)
        try:
            yield test_url
        finally:
            with _admin_connection(base_url) as admin:
                admin.execute(f'drop database if exists "{name}" with (force)')


CORPUS_TABLES = (
    "corpus.emb_openai_3l, corpus.emb_bge_m3, corpus.chunk, corpus.document, corpus.translation_group, "
    "corpus.fetch_state, corpus.quarantine, corpus.llm_spend, corpus.batch_job, corpus.source"
)


@pytest.fixture
def corpus_db() -> str:
    """A database with the public schema, the location tree, and an empty corpus schema."""
    from swiss_grounding.corpus.db import apply_corpus_schema
    from swiss_grounding.db.connection import connect
    from swiss_grounding.db.migrate import apply_schema
    from swiss_grounding.locations.repository import upsert_locations
    from swiss_grounding.locations.seed import seed_locations

    url = os.environ["DATABASE_URL"]
    apply_schema(url, 8)
    apply_corpus_schema(url)
    with connect(url) as conn:
        if conn.execute("select count(*) as n from location").fetchone()["n"] == 0:
            upsert_locations(conn, seed_locations())
        conn.execute(f"truncate {CORPUS_TABLES} restart identity cascade")
    return url


SERVING_TABLES = "serving.call_log, serving.lookup_cache, serving.premium_region, serving.premium"


@pytest.fixture
def serving_db(corpus_db) -> str:
    """corpus_db plus an empty serving schema."""
    from swiss_grounding.db.connection import connect
    from swiss_grounding.serving.db import apply_serving_schema

    apply_serving_schema(corpus_db)
    with connect(corpus_db) as conn:
        conn.execute(f"truncate {SERVING_TABLES} restart identity")
    return corpus_db
