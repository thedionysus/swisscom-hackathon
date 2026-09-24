import pytest

from swiss_grounding.evals.golden_models import GoldenSet
from swiss_grounding.evals.golden_runner import run_golden
from tests.integration.serving.corpus_fixture import add_doc
from tests.integration.serving.test_search_service import service

pytestmark = pytest.mark.integration

GOLDEN = GoldenSet.model_validate({"version": "t", "probes": [
    {"id": "g1", "question": "Kündigungsfrist Wohnung?", "language": "de", "area": "housing", "level": "federal",
     "split": "dev", "expect": {"status": "results", "sources": ["/or/"], "key_fact": "drei Monate"}},
    {"id": "g2", "question": "Rundfunkbeitrag?", "locations": ["Konstanz"], "language": "de", "area": "none",
     "level": "none", "split": "dev", "expect": {"status": "outside_scope"}},
]})


def test_run_reports_status_accuracy_and_recall(serving_db):
    from swiss_grounding.db.connection import connect
    with connect(serving_db) as conn:
        add_doc(conn, group="or", lang="de", text="Kündigungsfrist Wohnung drei Monate",
                url="https://fedlex/or/de")
    report = run_golden(service(serving_db), GOLDEN, labels={}, split="all")
    assert report.summary["status_accuracy"] == 1.0
    assert report.summary["recall@5"] == 1.0
    assert report.summary["precision@5"] is None
    assert [o.probe_id for o in report.outcomes] == ["g1", "g2"]
