from datetime import UTC, datetime

from typer.testing import CliRunner

from swiss_grounding.cli.eval_commands import _git_commit, _print_table, _status_mismatches
from swiss_grounding.cli.main import app
from swiss_grounding.evals.probe_models import Expectation, Observed, Probe
from swiss_grounding.evals.runner import ProbeResult
from swiss_grounding.retrieval.models import QueryResponse


def test_eval_commands_are_registered():
    result = CliRunner().invoke(app, ["eval", "--help"])
    assert result.exit_code == 0
    assert "probes" in result.output
    assert "judge" in result.output


def _result(pid: str, status: str, failures: tuple[str, ...]) -> ProbeResult:
    probe = Probe(id=pid, question="q", kind="structural", failure_class="none", status=status,
                  expect=Expectation(status="results"))
    obs = Observed(recorded_at=datetime.now(UTC), status="results", failures=failures)
    return ProbeResult(probe=probe, response=QueryResponse(status="results"), failures=failures, observed=obs)


def test_status_mismatches_flags_red_passing_and_green_failing():
    results = [
        ("city", _result("green-ok", "green", ())),
        ("city", _result("red-ok", "red", ("f",))),
        ("city", _result("green-bad", "green", ("f",))),
        ("city", _result("red-bad", "red", ())),
    ]
    assert _status_mismatches(results) == ["green-bad", "red-bad"]


def test_print_table_lists_failures(capsys):
    _print_table([("city", _result("p1", "green", ("status: expected results, got needs_location",)))])
    out = capsys.readouterr().out
    assert "p1" in out and "FAIL" in out and "needs_location" in out


def test_git_commit_returns_short_sha_or_none():
    sha = _git_commit()
    assert sha is None or (len(sha) >= 7 and all(c in "0123456789abcdef" for c in sha))
