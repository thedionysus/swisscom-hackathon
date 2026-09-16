"""Judge cases: answer with a model through claude -p and the MCP server, grade with a fixed judge."""
import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from swiss_grounding.evals.probe_models import Probe

JUDGE_MODEL = "claude-fable-5-1"
JUDGE_DIR = Path(__file__).resolve().parents[3] / "evals" / "judge"
MCP_CONFIG = JUDGE_DIR / "mcp.json"
RUBRIC = JUDGE_DIR / "rubric.md"
VERDICT_KEYS = (
    "jurisdiction_confusion", "authority_hierarchy", "temporal_misapplication",
    "entity_substitution", "silent_under_coverage", "url_grounded", "coverage_signal_repeated",
)
ANSWER_SYSTEM = (
    "Answer the user's question using only the swiss-grounding tools. Cite the URLs the tools "
    "return. If the tools say a location has no local data, say so."
)
STDERR_PREVIEW = 500
CLAUDE_TIMEOUT_SECONDS = 600


def _claude(prompt: str, model: str, *, mcp: bool, stream: bool) -> str:
    cmd = ["claude", "-p", prompt, "--model", model]
    if mcp:
        cmd += ["--mcp-config", str(MCP_CONFIG), "--allowedTools", "mcp__swiss-grounding__*",
                "--append-system-prompt", ANSWER_SYSTEM]
    else:
        cmd += ["--disallowedTools", "*"]
    if stream:
        cmd += ["--output-format", "stream-json", "--verbose"]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=CLAUDE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"claude timed out after {CLAUDE_TIMEOUT_SECONDS}s for model {model}") from exc
    if proc.returncode != 0:
        raise RuntimeError(
            f"claude exited {proc.returncode} for model {model}: {proc.stderr[:STDERR_PREVIEW]}")
    return proc.stdout


def _texts(content: object) -> list[str]:
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [c.get("text", "") for c in content if isinstance(c, Mapping) and c.get("type") == "text"]
    return []


def extract_tool_results(stream: str) -> tuple[list[str], str]:
    """Tool result texts and the final answer from a stream-json transcript; bad lines are skipped."""
    results: list[str] = []
    final = ""
    for line in stream.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            final = event.get("result", "")
            continue
        message = event.get("message")
        content = message.get("content") if isinstance(message, Mapping) else None
        if not isinstance(content, list):
            continue  # a bare string message carries no tool results
        for block in content:
            if isinstance(block, Mapping) and block.get("type") == "tool_result":
                results.extend(_texts(block.get("content", [])))
    return results, final


def build_judge_prompt(rubric: str, question: str, evidence: Sequence[str], answer: str) -> str:
    """Substitute the three placeholders without str.format, so braces in evidence survive."""
    return (rubric.replace("{question}", question)
                  .replace("{evidence}", "\n\n".join(evidence))
                  .replace("{answer}", answer))


def _last_json_object(text: str) -> dict | None:
    """Scan every '{' for a decodable JSON object; prefer the last one carrying a verdict key,
    falling back to the last dict decoded at all when none does."""
    decoder = json.JSONDecoder()
    found: dict | None = None
    for pos, char in enumerate(text):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text, pos)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and (found is None or any(k in obj for k in VERDICT_KEYS)):
            found = obj
    return found


def _is_true(value: object) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def parse_verdict(text: str) -> tuple[dict[str, bool], bool]:
    """Verdict keyed True/False, and whether a JSON object was found at all (last-object-wins)."""
    raw = _last_json_object(text)
    parsed = raw is not None
    raw = raw or {}
    return {k: _is_true(raw.get(k)) for k in VERDICT_KEYS}, parsed


# NOTE: as_of and categories are not passed to the answering model (only the question and
# location are). If a probe with as_of is ever flagged judge: true, this needs extending so the
# model has the same temporal frame the checker uses, or temporal_misapplication cases will be
# unfair to grade.
def _question_text(probe: Probe) -> str:
    return f"{probe.question} (location: {probe.location})" if probe.location else probe.question


def run_case(probe: Probe, model: str, rubric: str) -> dict:
    try:
        stream = _claude(_question_text(probe), model, mcp=True, stream=True)
        evidence, answer = extract_tool_results(stream)
        verdict_text = _claude(build_judge_prompt(rubric, _question_text(probe), evidence, answer),
                               JUDGE_MODEL, mcp=False, stream=False)
        verdict, parsed = parse_verdict(verdict_text)
        return {"probe_id": probe.id, "model": model, "answer": answer, "evidence": evidence,
                "verdict": verdict, "verdict_parsed": parsed, "error": None}
    except Exception as exc:  # noqa: BLE001 - one bad case must not end a paid run
        return {"probe_id": probe.id, "model": model, "answer": "", "evidence": [],
                "verdict": dict.fromkeys(VERDICT_KEYS, False), "verdict_parsed": False,
                "error": str(exc)}


def summary_table(records: Sequence[Mapping]) -> str:
    scored = [r for r in records if not r.get("error") and r.get("verdict_parsed")]
    models = list(dict.fromkeys(r["model"] for r in records))
    header = f"{'model':<32} " + " ".join(f"{k[:14]:<14}" for k in VERDICT_KEYS)
    rows = [header]
    for model in models:
        verdicts = [r["verdict"] for r in scored if r["model"] == model]
        if not verdicts:
            cells = ["0/0".ljust(14) for _ in VERDICT_KEYS]
        else:
            cells = [f"{sum(1 for v in verdicts if v.get(k))}/{len(verdicts)}".ljust(14)
                      for k in VERDICT_KEYS]
        rows.append(f"{model:<32} " + " ".join(cells))
    unscored = len(records) - len(scored)
    rows.append(f"unscored: {unscored} of {len(records)} (errors or unparseable verdicts)")
    return "\n".join(rows)


def _write_atomically(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def run_judge_suite(cases: Sequence[Probe], models: Sequence[str], out: Path) -> str:
    rubric = RUBRIC.read_text()
    jobs = [(m, p) for m in models for p in cases]
    total = len(jobs)
    records: list[dict] = []
    ran_at = datetime.now(UTC).isoformat()
    out.parent.mkdir(parents=True, exist_ok=True)
    for i, (model, probe) in enumerate(jobs, start=1):
        print(f"[{i}/{total}] {model} {probe.id}", file=sys.stderr)
        records.append(run_case(probe, model, rubric))
        _write_atomically(out, json.dumps(
            {"ran_at": ran_at, "judge": JUDGE_MODEL, "models": list(models), "records": records},
            indent=None, ensure_ascii=False))
    return summary_table(records)
