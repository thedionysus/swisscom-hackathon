from contextlib import contextmanager
from typing import Iterator

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row


@contextmanager
def connect(database_url: str) -> Iterator[psycopg.Connection]:
    """Open a connection with dict rows and pgvector registered. Commits on success."""
    conn = psycopg.connect(database_url, row_factory=dict_row)
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
