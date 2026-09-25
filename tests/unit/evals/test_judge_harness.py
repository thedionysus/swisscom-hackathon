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
from swiss_grounding.evals.openai_answer import mcp_http_url


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


def test_parse_verdict_with_faithfulness_keys():
    from swiss_grounding.evals.judge_harness import FAITHFULNESS_KEYS, parse_verdict
    verdict, parsed = parse_verdict('{"faithful": true, "unsupported_claims": [], "cited_urls_in_evidence": true}',
                                    FAITHFULNESS_KEYS)
    assert parsed and verdict == {"faithful": True, "cited_urls_in_evidence": True}


def test_faithfulness_rubric_fills_its_placeholders():
    rubric = (judge_harness.JUDGE_DIR / "faithfulness.md").read_text()
    prompt = build_judge_prompt(rubric, "Q?", ["E1"], "A.")
    assert "Q?" in prompt
    assert "E1" in prompt
    assert "A." in prompt
    assert "{question}" not in prompt
    assert "{evidence}" not in prompt
    assert "{answer}" not in prompt


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
    def fake_claude(prompt, model, *, mcp, stream, mcp_config=None):
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


def test_extract_tool_results_tolerates_string_message_content():
    lines = [
        json.dumps({"type": "assistant", "message": {"content": "just text"}}),
        json.dumps({"type": "system", "message": "not even a mapping"}),
        json.dumps({"type": "result", "result": "done"}),
    ]
    assert extract_tool_results("\n".join(lines)) == ([], "done")


def test_run_case_records_any_exception(monkeypatch):
    from swiss_grounding.evals import judge_harness
    from swiss_grounding.evals.probe_models import Expectation, Probe

    def boom(*args, **kwargs):
        raise AttributeError("'str' object has no attribute 'get'")

    monkeypatch.setattr(judge_harness, "_claude", boom)
    probe = Probe(id="p", question="q", kind="structural", failure_class="none", status="green",
                  expect=Expectation(status="results"))
    record = judge_harness.run_case(probe, "m", "rubric")
    assert "no attribute" in record["error"]
    assert record["verdict_parsed"] is False


def test_run_judge_suite_resume_keeps_clean_records_and_reruns_errors(monkeypatch, tmp_path):
    from swiss_grounding.evals.probe_models import Expectation, Probe

    all_true = dict.fromkeys(VERDICT_KEYS, True)
    out = tmp_path / "results.json"
    previous = {"records": [
        {"probe_id": "a", "model": "m", "answer": "ok", "evidence": [], "verdict": all_true,
         "verdict_parsed": True, "error": None},
        {"probe_id": "b", "model": "m", "answer": "", "evidence": [],
         "verdict": dict.fromkeys(VERDICT_KEYS, False), "verdict_parsed": False, "error": "boom"},
    ]}
    out.write_text(json.dumps(previous))
    ran: list[str] = []

    def fake_run_case(probe, model, rubric):
        ran.append(probe.id)
        return {"probe_id": probe.id, "model": model, "answer": "ok", "evidence": [],
                "verdict": all_true, "verdict_parsed": True, "error": None}

    monkeypatch.setattr(judge_harness, "run_case", fake_run_case)
    monkeypatch.setattr(judge_harness, "RUBRIC", tmp_path / "rubric.md")
    (tmp_path / "rubric.md").write_text("r")
    cases = [Probe(id=i, question="q", kind="structural", failure_class="none", status="green",
                   expect=Expectation(status="results")) for i in ("a", "b")]
    table = judge_harness.run_judge_suite(cases, ("m",), out, resume=True)
    assert ran == ["b"]
    assert "unscored: 0 of 2" in table
    assert len(json.loads(out.read_text())["records"]) == 2


def test_apertus_answers_through_the_openai_loop_and_claude_still_judges(monkeypatch):
    from swiss_grounding.evals import judge_harness as jh
    calls = []
    monkeypatch.setattr(jh, "_apertus_answer", lambda q, mcp_config: (calls.append(q) or (["ev"], "answer")))
    monkeypatch.setattr(jh, "_claude", lambda prompt, model, **kw: '{"faithful": true, "cited_urls_in_evidence": true}')
    record = jh.run_question("Frage?", "g1", "apertus", "{question}{evidence}{answer}")
    assert calls == ["Frage?"] and record["answer"] == "answer" and record["verdict"]["faithful"]


def test_apertus_answer_uses_an_http_config_it_is_given(monkeypatch, tmp_path):
    import swiss_grounding.config as config_module
    from swiss_grounding.evals import judge_harness as jh

    monkeypatch.setattr(config_module, "load_settings",
                        lambda: config_module.Settings(_env_file=None, database_url="postgresql://x",
                                                        apertus_api_key="k"))
    monkeypatch.setattr("openai.OpenAI", lambda **kw: object())
    captured = {}
    monkeypatch.setattr("swiss_grounding.evals.openai_answer.answer_with_tools",
                        lambda q, *, client, model, mcp_url, system: captured.update(mcp_url=mcp_url) or
                        (["ev"], "answer"))
    http_config = tmp_path / "http.json"
    http_config.write_text(json.dumps({"mcpServers": {"swiss-grounding": {"type": "http", "url": "http://h/mcp"}}}))
    result = jh._apertus_answer("q", http_config)
    assert result == (["ev"], "answer") and captured["mcp_url"] == "http://h/mcp"


def test_apertus_answer_falls_back_to_the_http_config_for_a_stdio_config(monkeypatch, tmp_path):
    import swiss_grounding.config as config_module
    from swiss_grounding.evals import judge_harness as jh

    monkeypatch.setattr(config_module, "load_settings",
                        lambda: config_module.Settings(_env_file=None, database_url="postgresql://x",
                                                        apertus_api_key="k"))
    monkeypatch.setattr("openai.OpenAI", lambda **kw: object())
    captured = {}
    monkeypatch.setattr("swiss_grounding.evals.openai_answer.answer_with_tools",
                        lambda q, *, client, model, mcp_url, system: captured.update(mcp_url=mcp_url) or
                        (["ev"], "answer"))
    stdio_config = tmp_path / "stdio.json"
    stdio_config.write_text(json.dumps({"mcpServers": {"swiss-grounding": {"command": "uv"}}}))
    result = jh._apertus_answer("q", stdio_config)
    assert result == (["ev"], "answer")
    assert captured["mcp_url"] == mcp_http_url(jh.MCP_HTTP_CONFIG)
