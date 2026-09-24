import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.serving.call_log import CallRecord, latency_summary, record_call

pytestmark = pytest.mark.integration


def test_records_calls_and_summarises_latency(serving_db):
    for ms in (100, 200, 300, 400):
        record_call(serving_db, CallRecord(tool="swiss_search", duration_ms=ms, status="results", places=1,
                                           citations=3, reranker="r"))
    record_call(serving_db, CallRecord(tool="swiss_search", duration_ms=50, status="no_evidence"))
    with connect(serving_db) as conn:
        [row] = latency_summary(conn)
    assert row["tool"] == "swiss_search" and row["calls"] == 5
    assert row["p50_ms"] == 200 and row["abstain_rate"] == 0.2


def test_logging_failure_never_raises():
    record_call("postgresql://nobody@127.0.0.1:1/none", CallRecord(tool="t", duration_ms=1, status="results"))
