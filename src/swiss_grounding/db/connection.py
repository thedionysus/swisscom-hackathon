from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row


@contextmanager
def connect(database_url: str, connect_timeout: int | None = None) -> Iterator[psycopg.Connection]:
    """Open a connection with dict rows and pgvector registered. Commits on success.

    `connect_timeout` (seconds) bounds how long the TCP connect attempt itself can take,
    for callers on a non-critical path (e.g. call logging) that must not hang on a dead host.
    """
    kwargs = {"connect_timeout": connect_timeout} if connect_timeout is not None else {}
    conn = psycopg.connect(database_url, row_factory=dict_row, **kwargs)
    try:
        conn.execute("create extension if not exists vector")
        register_vector(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
