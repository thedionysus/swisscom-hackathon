from datetime import UTC, date, datetime
from typing import ClassVar

from typer.testing import CliRunner

from swiss_grounding.cli import eval_commands
from swiss_grounding.cli.eval_commands import (
    SWISS_TZ,
    _git_commit,
    _print_table,
    _status_mismatches,
    _today,
)
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


def test_today_is_swiss_civil_date():
    assert isinstance(_today(), date)
    assert SWISS_TZ.key == "Europe/Zurich"


def test_probes_cmd_rejects_unknown_tier():
    result = CliRunner().invoke(app, ["eval", "probes", "--tier", "zurich"])
    assert result.exit_code == 2
    assert "zurich" in result.output


class _StubTree:
    by_id: ClassVar[dict] = {}

    def path(self, node_id):
        return ()


class _StubCore:
    tree = _StubTree()

    def query(self, request):
        return QueryResponse(status="needs_location")


class _StubConn:
    def execute(self, *args, **kwargs):
        return None


class _StubConnectionCM:
    def __enter__(self):
        return _StubConn()

    def __exit__(self, *args):
        return False


def test_probes_cmd_exit_code_on_status_mismatch(monkeypatch):
    probe = Probe(id="p-mismatch", question="q", kind="structural", failure_class="none",
                  status="green", expect=Expectation(status="results"))
    monkeypatch.setattr(eval_commands, "build_query_core", lambda settings: _StubCore())
    monkeypatch.setattr(eval_commands, "connect", lambda url: _StubConnectionCM())
    monkeypatch.setattr(eval_commands, "load_all_probes", lambda probe_dir: (("city", probe),))
    result = CliRunner().invoke(app, ["eval", "probes"])
    assert result.exit_code == 3
    assert "p-mismatch" in result.output
