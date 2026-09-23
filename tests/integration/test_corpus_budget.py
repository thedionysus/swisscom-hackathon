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
    while the first run's batches are pending. A batch that is already ingested, or that ended
    failed/expired/cancelled, does not count."""
    with connect(corpus_db) as conn:
        def insert(batch_id, kind, status, estimated_usd, ingested):
            ingested_at_sql = "now()" if ingested else "null"
            conn.execute(
                "insert into corpus.batch_job (id, kind, endpoint, status, request_count, input_path, "
                f"estimated_usd, ingested_at) values (%s,%s,%s,%s,%s,%s,%s,{ingested_at_sql})",
                (batch_id, kind, "/v1/chat/completions", status, 10, f"/tmp/{batch_id}.jsonl", estimated_usd),
            )

        # The one row that should count: still in flight, not yet ingested.
        insert("batch-1", "describe-chunk", "in_progress", 20.0, ingested=False)
        # Terminal-failed and terminal-cancelled batches no longer count, even unfinished.
        insert("batch-2", "ocr", "failed", 50.0, ingested=False)
        insert("batch-3", "embed", "expired", 30.0, ingested=False)
        insert("batch-4", "describe-doc", "cancelled", 40.0, ingested=False)
        # A completed batch that has already been ingested no longer counts either.
        insert("batch-5", "describe-chunk", "completed", 60.0, ingested=True)

        assert spent(conn) == pytest.approx(0.0)
        assert spent(conn, kind="describe") == pytest.approx(0.0)
        assert spent(conn, kind="ocr") == pytest.approx(0.0)
        ensure_within(conn, estimate=79.0, total_cap=100.0)
        with pytest.raises(BudgetExceeded, match="total"):
            ensure_within(conn, estimate=81.0, total_cap=100.0)
        with pytest.raises(BudgetExceeded, match="describe"):
            ensure_within(conn, estimate=1.0, total_cap=100.0, kind="describe", kind_cap=20.0)
