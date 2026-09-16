"""Judge cases: answer with a model through claude -p and the MCP server, grade with a fixed judge."""
import json
import re
import subprocess
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
JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)
STDERR_PREVIEW = 500


def _claude(prompt: str, model: str, *, mcp: bool, stream: bool) -> str:
    cmd = ["claude", "-p", prompt, "--model", model]
    if mcp:
        cmd += ["--mcp-config", str(MCP_CONFIG), "--allowedTools", "mcp__swiss-grounding__*",
                "--append-system-prompt", ANSWER_SYSTEM]
    if stream:
        cmd += ["--output-format", "stream-json", "--verbose"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
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
        for block in event.get("message", {}).get("content", []):
            if isinstance(block, Mapping) and block.get("type") == "tool_result":
                results.extend(_texts(block.get("content", [])))
    return results, final


def build_judge_prompt(rubric: str, question: str, evidence: Sequence[str], answer: str) -> str:
    """Substitute the three placeholders without str.format, so braces in evidence survive."""
    return (rubric.replace("{question}", question)
                  .replace("{evidence}", "\n\n".join(evidence))
                  .replace("{answer}", answer))


def parse_verdict(text: str) -> dict[str, bool]:
    match = JSON_OBJECT.search(text)
    try:
        raw = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        raw = {}
    return {k: bool(raw.get(k, False)) for k in VERDICT_KEYS}


def _question_text(probe: Probe) -> str:
    return f"{probe.question} (location: {probe.location})" if probe.location else probe.question


def run_case(probe: Probe, model: str, rubric: str) -> dict:
    stream = _claude(_question_text(probe), model, mcp=True, stream=True)
    evidence, answer = extract_tool_results(stream)
    verdict_text = _claude(build_judge_prompt(rubric, _question_text(probe), evidence, answer),
                           JUDGE_MODEL, mcp=False, stream=False)
    return {"probe_id": probe.id, "model": model, "answer": answer, "evidence": evidence,
            "verdict": parse_verdict(verdict_text)}


def summary_table(verdicts_by_model: Mapping[str, Sequence[Mapping[str, bool]]]) -> str:
    header = f"{'model':<32} " + " ".join(f"{k[:14]:<14}" for k in VERDICT_KEYS)
    rows = [header]
    for model, verdicts in verdicts_by_model.items():
        cells = [f"{sum(1 for v in verdicts if v.get(k))}/{len(verdicts)}".ljust(14) for k in VERDICT_KEYS]
        rows.append(f"{model:<32} " + " ".join(cells))
    return "\n".join(rows)


def run_judge_suite(cases: Sequence[Probe], models: Sequence[str], out: Path) -> str:
    rubric = RUBRIC.read_text()
    records = [run_case(p, m, rubric) for m in models for p in cases]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"ran_at": datetime.now(UTC).isoformat(), "judge": JUDGE_MODEL,
                               "records": records}, indent=2, ensure_ascii=False))
    by_model = {m: [r["verdict"] for r in records if r["model"] == m] for m in models}
    return summary_table(by_model)
