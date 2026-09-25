"""Unit tests for `--source` filtering in the describe module: no database, a stub connection records
the SQL text and bound params so we can assert the source list is always a parameter, never formatted
into the query string."""
from swiss_grounding.corpus.describe import (
    CHUNK_TEXT_CHARS,
    PENDING_CHUNKS,
    _pending_chunks_sql,
    build_chunk_tasks,
    build_doc_tasks,
    known_source_ids,
    validate_sources,
)


class _Recorder:
    """Captures every `execute` call; `fetchall`/`fetchone` return canned rows for the next call."""

    def __init__(self, rows=()):
        self.calls = []
        self._rows = rows

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return self

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


def test_pending_chunks_sql_adds_a_bound_source_filter_only_when_sources_are_given():
    assert _pending_chunks_sql(()) == PENDING_CHUNKS
    filtered = _pending_chunks_sql(("bazg",))
    assert "d.source_id = any(%s)" in filtered
    assert "bazg" not in filtered  # the id is never formatted into the SQL text


def test_build_doc_tasks_binds_the_source_list_as_a_query_parameter():
    conn = _Recorder(rows=[])
    build_doc_tasks(conn, "gpt-5-mini", limit=10, sources=("bazg", "bk_votes"))
    sql, params = conn.calls[0]
    assert "d.source_id = any(%s)" in sql
    assert params == (["bazg", "bk_votes"], 10)


def test_build_doc_tasks_has_no_filter_without_sources():
    conn = _Recorder(rows=[])
    build_doc_tasks(conn, "gpt-5-mini", limit=10)
    sql, params = conn.calls[0]
    assert "source_id" not in sql
    assert params == (10,)


def test_build_chunk_tasks_binds_the_source_list_between_the_text_cap_and_the_limit():
    conn = _Recorder(rows=[])
    build_chunk_tasks(conn, "gpt-5-nano", limit=5, sources=("bazg",))
    sql, params = conn.calls[0]
    assert "d.source_id = any(%s)" in sql
    assert params == (CHUNK_TEXT_CHARS, ["bazg"], 5)


def test_build_chunk_tasks_has_no_filter_without_sources():
    conn = _Recorder(rows=[])
    build_chunk_tasks(conn, "gpt-5-nano", limit=5)
    sql, params = conn.calls[0]
    assert "source_id" not in sql
    assert params == (CHUNK_TEXT_CHARS, 5)


def test_known_source_ids_reads_corpus_source():
    conn = _Recorder(rows=[{"id": "bazg"}, {"id": "bk_votes"}])
    assert known_source_ids(conn) == {"bazg", "bk_votes"}


def test_validate_sources_lists_every_unknown_id():
    conn = _Recorder(rows=[{"id": "bazg"}])
    try:
        validate_sources(conn, ("bazg", "bogus", "missing"))
    except ValueError as exc:
        assert "bogus" in str(exc) and "missing" in str(exc)
    else:
        raise AssertionError("expected ValueError for unknown source ids")


def test_validate_sources_passes_when_every_id_is_known():
    conn = _Recorder(rows=[{"id": "bazg"}])
    validate_sources(conn, ("bazg",))  # no error
