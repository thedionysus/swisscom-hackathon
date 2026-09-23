import pytest

from swiss_grounding.corpus.budget import BudgetExceeded, ensure_within, record_spend, spent
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration


def test_ledger_and_caps(corpus_db):
    with connect(corpus_db) as conn:
        record_spend(conn, kind="describe", model="gpt-5-nano", usd=60.0, input_tokens=1, output_tokens=1, estimated=False)
        record_spend(conn, kind="ocr", model="gpt-5-mini", usd=9.0, input_tokens=1, output_tokens=1, estimated=False)
        assert spent(conn) == pytest.approx(69.0)
        assert spent(conn, kind="ocr") == pytest.approx(9.0)
        ensure_within(conn, estimate=30.0, total_cap=100.0)
        with pytest.raises(BudgetExceeded, match="total"):
            ensure_within(conn, estimate=32.0, total_cap=100.0)
        with pytest.raises(BudgetExceeded, match="ocr"):
            ensure_within(conn, estimate=2.0, total_cap=100.0, kind="ocr", kind_cap=10.0)


def test_in_flight_batch_jobs_count_against_the_cap(corpus_db):
    """A3: a batch job not yet ingested still counts, so a second run can't blow past the cap
    while the first run's batches are pending. A terminal-failed batch does not count."""
    with connect(corpus_db) as conn:
        conn.execute(
            "insert into corpus.batch_job (id, kind, endpoint, status, request_count, input_path, estimated_usd) "
            "values (%s,%s,%s,%s,%s,%s,%s)",
            ("batch-1", "describe-chunk", "/v1/chat/completions", "in_progress", 10, "/tmp/a.jsonl", 20.0),
        )
        conn.execute(
            "insert into corpus.batch_job (id, kind, endpoint, status, request_count, input_path, estimated_usd) "
            "values (%s,%s,%s,%s,%s,%s,%s)",
            ("batch-2", "ocr", "/v1/chat/completions", "failed", 10, "/tmp/b.jsonl", 50.0),
        )
        assert spent(conn) == pytest.approx(0.0)
        assert spent(conn, kind="describe") == pytest.approx(0.0)
        assert spent(conn, kind="ocr") == pytest.approx(0.0)
        with pytest.raises(BudgetExceeded, match="total"):
            ensure_within(conn, estimate=85.0, total_cap=100.0)
        with pytest.raises(BudgetExceeded, match="describe"):
            ensure_within(conn, estimate=1.0, total_cap=100.0, kind="describe", kind_cap=20.0)
