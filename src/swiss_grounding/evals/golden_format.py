"""Text rendering and JSON payload of the golden report's statistics."""
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any

from swiss_grounding.evals.golden_analysis import (
    Stat,
    abstention,
    confusion,
    headline,
    latency,
    slices,
)
from swiss_grounding.evals.golden_runner import GoldenReport, ProbeOutcome
from swiss_grounding.evals.metrics import THRESHOLDS, passes

SLICE_METRICS = ("status_accuracy", "recall@5", "hit@1", "mrr@5", "leakage@5", "lang_match@1")


def _num(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.3f}"


def stat_line(name: str, s: Stat, verdict: Mapping[str, bool]) -> str:
    ci = f"[{s.ci[0]:.2f}, {s.ci[1]:.2f}]" if s.ci else "[n/a]"
    gate = ("PASS" if verdict.get(name) else "FAIL") if name in THRESHOLDS else ""
    return f"{name:<22} {_num(s.value):<6} {ci:<13} n={s.n:<4} {gate}".rstrip()


def headline_lines(outcomes: Sequence[ProbeOutcome], summary: Mapping[str, float | None]) -> list[str]:
    verdict = passes(summary)
    return [stat_line(name, s, verdict) for name, s in headline(outcomes).items()]


def confusion_lines(outcomes: Sequence[ProbeOutcome]) -> list[str]:
    matrix = confusion(outcomes)
    got = sorted({g for row in matrix.values() for g in row})
    head = f"{'expected \\ got':<28}" + "".join(f"{g[:14]:>15}" for g in got)
    rows = [f"{want[:28]:<28}" + "".join(f"{row.get(g, 0):>15}" for g in got) for want, row in matrix.items()]
    return [head, *rows]


def slice_lines(outcomes: Sequence[ProbeOutcome]) -> list[str]:
    lines: list[str] = []
    for key, groups in slices(outcomes).items():
        lines.append(f"-- by {key}")
        lines.append(f"{'':<18}{'n':>4}" + "".join(f"{m:>16}" for m in SLICE_METRICS))
        for value, stats in groups.items():
            cells = "".join(f"{_num(stats[m].value) + f' ({stats[m].n})':>16}" for m in SLICE_METRICS)
            lines.append(f"{value[:18]:<18}{stats['status_accuracy'].n:>4}{cells}")
    return lines


def latency_line(outcomes: Sequence[ProbeOutcome]) -> str:
    lat = latency(outcomes)
    return f"latency_s  p50={_num(lat['p50'])}  p95={_num(lat['p95'])}  max={_num(lat['max'])}"


def report_payload(report: GoldenReport) -> dict[str, Any]:
    """The recorded run: the report plus every statistic, JSON-ready."""
    o = report.outcomes
    return {**asdict(report),
            "headline": {name: asdict(s) for name, s in headline(o).items()},
            "abstention": abstention(o), "confusion": confusion(o), "latency": latency(o),
            "slices": {key: {v: {m: asdict(s) for m, s in stats.items()} for v, stats in groups.items()}
                       for key, groups in slices(o).items()}}


def compare_lines(result: Mapping[str, Any]) -> list[str]:
    lines = [f"{'metric':<22} {'before':>7} {'after':>7} {'delta':>8}"]
    for name, (old, new, delta) in result["deltas"].items():
        shown = "n/a" if delta is None else f"{delta:+.3f}"
        lines.append(f"{name:<22} {_num(old):>7} {_num(new):>7} {shown:>8}")
    for label in ("pass_to_fail", "fail_to_pass", "new", "removed"):
        ids = result[label]
        lines.append(f"{label} ({len(ids)}): {', '.join(ids) if ids else '-'}")
    return lines
