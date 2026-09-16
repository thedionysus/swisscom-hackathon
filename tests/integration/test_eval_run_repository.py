import os
from datetime import UTC, datetime

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.evals.eval_run_repository import insert_results, latest_run_summary
from swiss_grounding.evals.probe_models import Expectation, Observed, Probe
from swiss_grounding.evals.runner import ProbeResult
from swiss_grounding.retrieval.models import QueryResponse

pytestmark = pytest.mark.integration


def _result(pid: str, failures: tuple[str, ...]) -> ProbeResult:
    probe = Probe(id=pid, question="q", kind="structural", failure_class="none", status="green",
                  expect=Expectation(status="results"))
    obs = Observed(recorded_at=datetime.now(UTC), status="results", failures=failures)
    return ProbeResult(probe=probe, response=QueryResponse(status="results"), failures=failures, observed=obs)


def test_insert_and_summarise():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        conn.execute("truncate eval_run")
        insert_results(conn, run_id="r1", git_commit="abc", tier="city",
                       results=(_result("a", ()), _result("b", ("status: x",))))
        summary = latest_run_summary(conn)
        rows = conn.execute("select probe_id, passed, failures, observed from eval_run order by probe_id").fetchall()
    assert summary == {"run_id": "r1", "total": 2, "passed": 1, "failed": 1}
    assert rows[0]["probe_id"] == "a" and rows[0]["passed"] is True and rows[0]["failures"] == []
    assert rows[1]["failures"] == ["status: x"]
    assert rows[1]["observed"]["status"] == "results"


def test_latest_run_summary_none_when_empty():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        conn.execute("truncate eval_run")
        assert latest_run_summary(conn) is None


def test_latest_run_picks_most_recent_run():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        conn.execute("truncate eval_run")
        insert_results(conn, run_id="old", git_commit=None, tier="city", results=(_result("a", ()),))
        insert_results(conn, run_id="new", git_commit=None, tier="city", results=(_result("a", ("f",)),))
        assert latest_run_summary(conn)["run_id"] == "new"
