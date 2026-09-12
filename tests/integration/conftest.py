"""Integration test session setup.

The suite provisions its own throwaway database on the server named by DATABASE_URL
and points DATABASE_URL at it for the whole session. This keeps the 8-dimension test
schema from colliding with a quick-start database created by `db init` (vector(1024)),
and leaves the developer's demo data untouched.
"""

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest

TEST_DB_PREFIX = "swiss_grounding_test_"


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
        try:
            yield test_url
        finally:
            with _admin_connection(base_url) as admin:
                admin.execute(f'drop database if exists "{name}" with (force)')
