import json
import subprocess

import pytest

from swiss_grounding.evals import judge_harness
from swiss_grounding.evals.judge_harness import (
    VERDICT_KEYS,
    build_judge_prompt,
    extract_tool_results,
    parse_verdict,
    run_judge_suite,
    summary_table,
)


def test_extract_tool_results_from_stream_json():
    lines = [
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}}),
        json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1",
             "content": [{"type": "text", "text": "{\"status\": \"results\"}"}]},
        ]}}),
        json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t2", "content": "plain string result"},
        ]}}),
        "",
        json.dumps({"type": "result", "result": "final answer"}),
    ]
    tool_results, final = extract_tool_results("\n".join(lines))
    assert tool_results == ['{"status": "results"}', "plain string result"]
    assert final == "final answer"


def test_extract_tool_results_tolerates_non_json_lines():
    stream = "not json\n" + json.dumps({"type": "result", "result": "x"})
    assert extract_tool_results(stream) == ([], "x")


def test_parse_verdict_reads_json_object_anywhere_in_text():
    text = "Here is my grading:\n```json\n" + json.dumps(dict.fromkeys(VERDICT_KEYS, True)) + "\n```"
    verdict, parsed = parse_verdict(text)
    assert parsed is True
    assert all(verdict[k] is True for k in VERDICT_KEYS)


def test_parse_verdict_missing_key_is_false_and_no_json_is_all_false():
    verdict, parsed = parse_verdict(json.dumps({"jurisdiction_confusion": True}))
    assert parsed is True
    assert verdict["jurisdiction_confusion"] is True
    assert verdict["coverage_signal_repeated"] is False
    no_json_verdict, no_json_parsed = parse_verdict("no json here")
    assert no_json_parsed is False
    assert no_json_verdict == dict.fromkeys(VERDICT_KEYS, False)


def test_parse_verdict_takes_last_json_object():
    example = dict.fromkeys(VERDICT_KEYS, False)
    real = {**dict.fromkeys(VERDICT_KEYS, False), "url_grounded": True}
    text = f"Example: {json.dumps(example)}\nActual: {json.dumps(real)}"
    verdict, parsed = parse_verdict(text)
    assert parsed is True
    assert verdict["url_grounded"] is True


def test_parse_verdict_string_false_is_false():
    raw = {**dict.fromkeys(VERDICT_KEYS, "true"), "url_grounded": "false"}
    verdict, parsed = parse_verdict(json.dumps(raw))
    assert parsed is True
    assert verdict["url_grounded"] is False
    assert verdict["jurisdiction_confusion"] is True


def test_parse_verdict_ignores_trailing_nested_object():
    raw = {**dict.fromkeys(VERDICT_KEYS, True), "notes": {"why": "ok"}}
    verdict, parsed = parse_verdict(json.dumps(raw))
    assert parsed is True
    assert all(verdict[k] is True for k in VERDICT_KEYS)


def test_build_judge_prompt_includes_question_evidence_and_answer():
    prompt = build_judge_prompt("rubric {question} {evidence} {answer}", "Q?", ["E1", "E2"], "A.")
    assert "Q?" in prompt and "E1" in prompt and "E2" in prompt and "A." in prompt


def test_build_judge_prompt_survives_braces_in_evidence():
    prompt = build_judge_prompt("r {question} {evidence} {answer}", "Q", ['{"a": 1}'], "{b}")
    assert '{"a": 1}' in prompt and "{b}" in prompt


def test_summary_table_one_row_per_model():
    all_true = {**dict.fromkeys(VERDICT_KEYS, True)}
    good = {"model": "claude-sonnet-5", "verdict": all_true, "verdict_parsed": True, "error": None}
    partial = {"model": "claude-sonnet-5", "verdict": {**all_true, "url_grounded": False},
               "verdict_parsed": True, "error": None}
    table = summary_table([good, partial])
    assert "claude-sonnet-5" in table
    assert "url_grounded" in table
    assert "1/2" in table


def test_summary_table_excludes_errors_and_unparsed_and_reports_unscored():
    all_true = dict.fromkeys(VERDICT_KEYS, True)
    scored = {"model": "m", "verdict": all_true, "verdict_parsed": True, "error": None}
    errored = {"model": "m", "verdict": dict.fromkeys(VERDICT_KEYS, False), "verdict_parsed": False,
               "error": "claude exited 1"}
    table = summary_table([scored, errored])
    assert "1/1" in table
    assert "unscored: 1 of 2" in table


def _fake_run(returncode=0, stdout="", stderr=""):
    def run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)
    return run


def test_claude_answer_call_argv_shape(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(cmd, 0, stdout="out", stderr="")

    monkeypatch.setattr(judge_harness.subprocess, "run", fake_run)
    result = judge_harness._claude("question", "claude-sonnet-5", mcp=True, stream=True)
    assert result == "out"
    cmd = captured["cmd"]
    assert cmd[:2] == ["claude", "-p"]
    assert "--mcp-config" in cmd
    assert "--allowedTools" in cmd
    assert "--append-system-prompt" in cmd
    assert "--output-format" in cmd and "stream-json" in cmd
    assert "--verbose" in cmd
    assert captured["kwargs"]["timeout"] == judge_harness.CLAUDE_TIMEOUT_SECONDS


def test_claude_judge_call_argv_shape_is_toolless_and_not_streamed(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="out", stderr="")

    monkeypatch.setattr(judge_harness.subprocess, "run", fake_run)
    judge_harness._claude("prompt", judge_harness.JUDGE_MODEL, mcp=False, stream=False)
    cmd = captured["cmd"]
    assert "--mcp-config" not in cmd
    assert "--output-format" not in cmd
    assert "--disallowedTools" in cmd
    assert cmd[cmd.index("--disallowedTools") + 1] == "*"


def test_claude_raises_runtime_error_on_nonzero_exit(monkeypatch):
    monkeypatch.setattr(judge_harness.subprocess, "run",
                         _fake_run(returncode=1, stdout="", stderr="boom"))
    with pytest.raises(RuntimeError, match="claude exited 1"):
        judge_harness._claude("q", "m", mcp=True, stream=True)


def test_claude_raises_runtime_error_on_timeout(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, judge_harness.CLAUDE_TIMEOUT_SECONDS)

    monkeypatch.setattr(judge_harness.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="timed out"):
        judge_harness._claude("q", "m", mcp=True, stream=True)


def test_run_case_records_error_when_claude_fails(monkeypatch):
    def fake_claude(prompt, model, *, mcp, stream):
        raise RuntimeError("boom")

    monkeypatch.setattr(judge_harness, "_claude", fake_claude)

    class FakeProbe:
        id = "p1"
        question = "Q"
        location = None

    record = judge_harness.run_case(FakeProbe(), "claude-sonnet-5", "rubric")
    assert record["error"] == "boom"
    assert record["verdict_parsed"] is False
    assert record["answer"] == ""
    assert all(v is False for v in record["verdict"].values())


def test_run_judge_suite_writes_file_and_reports_unscored(monkeypatch, tmp_path):
    all_true = dict.fromkeys(VERDICT_KEYS, True)

    def fake_run_case(probe, model, rubric):
        if probe.id == "bad":
            return {"probe_id": probe.id, "model": model, "answer": "", "evidence": [],
                     "verdict": dict.fromkeys(VERDICT_KEYS, False), "verdict_parsed": False,
                     "error": "claude exited 1: boom"}
        return {"probe_id": probe.id, "model": model, "answer": "ok", "evidence": ["e"],
                "verdict": all_true, "verdict_parsed": True, "error": None}

    monkeypatch.setattr(judge_harness, "run_case", fake_run_case)

    class FakeProbe:
        def __init__(self, probe_id):
            self.id = probe_id
            self.question = "Q"
            self.location = None

    out = tmp_path / "results.json"
    table = run_judge_suite([FakeProbe("good"), FakeProbe("bad")], ["claude-sonnet-5"], out)

    written = json.loads(out.read_text())
    assert "records" in written
    assert "models" in written
    assert written["models"] == ["claude-sonnet-5"]
    assert len(written["records"]) == 2
    assert "unscored: 1 of 2" in table
