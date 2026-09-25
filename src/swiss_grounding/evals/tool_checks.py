"""Exact checks of the non-search tools against their golden probes. Pure; the caller supplies outputs."""
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from swiss_grounding.evals.golden_models import REMOTE_PREFIX, SEARCH_TOOL, GoldenProbe, GoldenSet

_MISSING = object()
# Listed tool names plus one output per call (None when the tool is not listed).
Caller = Callable[[Sequence[tuple[str, Mapping[str, Any]]]], tuple[frozenset[str], tuple[dict | None, ...]]]


@dataclass(frozen=True)
class ToolOutcome:
    probe_id: str
    tool: str
    passed: bool
    skipped: bool = False
    reason: str = ""


@dataclass(frozen=True)
class ToolReport:
    version: str
    outcomes: tuple[ToolOutcome, ...]
    summary: dict[str, int]


def lookup(body: Any, path: str) -> Any:
    """A dotted path into nested dicts and lists (list steps are indices)."""
    for step in path.split("."):
        if isinstance(body, list) and step.isdigit() and int(step) < len(body):
            body = body[int(step)]
        elif isinstance(body, dict) and step in body:
            body = body[step]
        else:
            return _MISSING
    return body


def _failures(probe: GoldenProbe, out: dict) -> list[str]:
    exp, errors = probe.expect, []
    status = out.get("status", "results")
    if status != exp.status:
        errors.append(f"status {status} (want {exp.status})")
    text = json.dumps(out, ensure_ascii=False, default=str)
    errors += [f"missing {s!r}" for s in exp.contains if s not in text]
    errors += [f"empty {p}" for p in exp.nonempty if lookup(out, p) in (_MISSING, None, "", [], {})]
    if exp.value_path is not None:
        got = lookup(out, exp.value_path)
        if not isinstance(got, (int, float)) or abs(got - exp.value) > exp.tolerance:
            errors.append(f"{exp.value_path}={None if got is _MISSING else got} (want {exp.value}±{exp.tolerance})")
    return errors


def check_tool(probe: GoldenProbe, out: dict | None) -> ToolOutcome:
    if out is None:
        why = ("zbern tools not served (ZBERN_MCP_TOKEN missing or zbern.ch unreachable)"
               if probe.tool.startswith(REMOTE_PREFIX) else "tool not listed by the server")
        return ToolOutcome(probe.id, probe.tool, False, skipped=True, reason=why)
    errors = _failures(probe, out)
    return ToolOutcome(probe.id, probe.tool, not errors, reason="; ".join(errors))


def run_tools(golden: GoldenSet, caller: Caller, split: str = "all") -> ToolReport:
    probes = [p for p in golden.probes if p.tool != SEARCH_TOOL and split in ("all", p.split)]
    _, outs = caller([(p.tool, p.args) for p in probes])
    outcomes = tuple(check_tool(p, o) for p, o in zip(probes, outs, strict=True))
    summary = {"passed": sum(o.passed for o in outcomes),
               "failed": sum(not o.passed and not o.skipped for o in outcomes),
               "skipped": sum(o.skipped for o in outcomes)}
    return ToolReport(golden.version, outcomes, summary)
