import json

from swiss_grounding.evals.judge_harness import (
    VERDICT_KEYS,
    build_judge_prompt,
    extract_tool_results,
    parse_verdict,
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
    verdict = parse_verdict(text)
    assert all(verdict[k] is True for k in VERDICT_KEYS)


def test_parse_verdict_missing_key_is_false_and_no_json_is_all_false():
    verdict = parse_verdict(json.dumps({"jurisdiction_confusion": True}))
    assert verdict["jurisdiction_confusion"] is True
    assert verdict["coverage_signal_repeated"] is False
    assert parse_verdict("no json here") == dict.fromkeys(VERDICT_KEYS, False)


def test_build_judge_prompt_includes_question_evidence_and_answer():
    prompt = build_judge_prompt("rubric {question} {evidence} {answer}", "Q?", ["E1", "E2"], "A.")
    assert "Q?" in prompt and "E1" in prompt and "E2" in prompt and "A." in prompt


def test_build_judge_prompt_survives_braces_in_evidence():
    prompt = build_judge_prompt("r {question} {evidence} {answer}", "Q", ['{"a": 1}'], "{b}")
    assert '{"a": 1}' in prompt and "{b}" in prompt


def test_summary_table_one_row_per_model():
    all_true = dict.fromkeys(VERDICT_KEYS, True)
    verdicts = {"claude-sonnet-5": [all_true, {**all_true, "url_grounded": False}]}
    table = summary_table(verdicts)
    assert "claude-sonnet-5" in table
    assert "url_grounded" in table
    assert "1/2" in table
