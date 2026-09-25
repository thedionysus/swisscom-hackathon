import json

from swiss_grounding.evals.golden_analysis import Stat
from swiss_grounding.evals.golden_format import report_payload, stat_line
from swiss_grounding.evals.golden_runner import GoldenReport, ProbeOutcome


def test_stat_line_shows_value_ci_n_and_gate():
    line = stat_line("status_accuracy", Stat(0.8125, (0.70, 0.894), 64), {"status_accuracy": False})
    assert line == "status_accuracy        0.812  [0.70, 0.89]  n=64   FAIL"


def test_payload_is_json_ready():
    o = ProbeOutcome("a", "results", "results", ("u",), 1.0, None, None, language="de", latency_s=0.2)
    payload = report_payload(GoldenReport("v1", "dev", (o,), {"status_accuracy": 1.0}))
    assert json.loads(json.dumps(payload))["slices"]["language"]["de"]["status_accuracy"]["n"] == 1
