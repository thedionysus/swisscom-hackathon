"""Headline metrics with intervals, abstention confusion, slices and run comparison for the golden set."""
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from swiss_grounding.evals.metrics import mean
from swiss_grounding.evals.stats import bootstrap_ci, percentile, wilson

if TYPE_CHECKING:
    from swiss_grounding.evals.golden_runner import ProbeOutcome

ANSWER = "results"
SLICE_KEYS = ("level", "language", "area", "canton")


@dataclass(frozen=True)
class Stat:
    value: float | None
    ci: tuple[float, float] | None
    n: int


def _proportion(flags: Sequence[bool]) -> Stat:
    hits = sum(flags)
    return Stat(hits / len(flags) if flags else None, wilson(hits, len(flags)) if flags else None, len(flags))


def _average(values: Sequence[float | None]) -> Stat:
    present = [v for v in values if v is not None]
    return Stat(mean(present), bootstrap_ci(present), len(present))


def _answered(o: "ProbeOutcome") -> bool:
    return ANSWER in o.status.split(",")


def _wants_answer(o: "ProbeOutcome") -> bool:
    return ANSWER in o.expected_status.split(",")


def headline(outcomes: Sequence["ProbeOutcome"]) -> dict[str, Stat]:
    ab = abstention(outcomes)
    return {
        "status_accuracy": _proportion([o.status == o.expected_status for o in outcomes]),
        "recall@5": _average([o.recall for o in outcomes]),
        "precision@5": _average([o.precision for o in outcomes]),
        "ndcg@5": _average([o.ndcg for o in outcomes]),
        "hit@1": _average([o.hit1 for o in outcomes]),
        "mrr@5": _average([o.mrr for o in outcomes]),
        "leakage@5": _average([o.leakage for o in outcomes]),
        "lang_match@1": _proportion([o.lang_match for o in outcomes if o.lang_match is not None]),
        "false_answer_rate": _rate(*ab["false_answer_rate"]),
        "false_abstention_rate": _rate(*ab["false_abstention_rate"]),
    }


def _rate(k: int, n: int) -> Stat:
    return Stat(k / n if n else None, wilson(k, n) if n else None, n)


def summary_values(outcomes: Sequence["ProbeOutcome"]) -> dict[str, float | None]:
    return {name: s.value for name, s in headline(outcomes).items()}


def abstention(outcomes: Sequence["ProbeOutcome"]) -> dict[str, tuple[int, int]]:
    """(count, denominator): answered though no answer was expected; abstained though one was."""
    no_answer = [o for o in outcomes if not _wants_answer(o)]
    answer = [o for o in outcomes if _wants_answer(o)]
    return {"false_answer_rate": (sum(_answered(o) for o in no_answer), len(no_answer)),
            "false_abstention_rate": (sum(not _answered(o) for o in answer), len(answer))}


def confusion(outcomes: Sequence["ProbeOutcome"]) -> dict[str, dict[str, int]]:
    counts = Counter((o.expected_status, o.status) for o in outcomes)
    matrix: dict[str, dict[str, int]] = {}
    for (want, got), n in sorted(counts.items()):
        matrix = {**matrix, want: {**matrix.get(want, {}), got: n}}
    return matrix


def latency(outcomes: Sequence["ProbeOutcome"]) -> dict[str, float | None]:
    times = [o.latency_s for o in outcomes if o.latency_s is not None]
    return {"p50": percentile(times, 50), "p95": percentile(times, 95), "max": max(times, default=None)}


def slices(outcomes: Sequence["ProbeOutcome"],
           keys: Sequence[str] = SLICE_KEYS) -> dict[str, dict[str, dict[str, Stat]]]:
    def group(attr: Callable[["ProbeOutcome"], Any]) -> dict[str, dict[str, Stat]]:
        values = sorted({str(attr(o)) for o in outcomes})
        return {v: headline([o for o in outcomes if str(attr(o)) == v]) for v in values}
    return {key: group(lambda o, key=key: getattr(o, key) or "-") for key in keys}


def compare(old: Mapping[str, Any], new: Mapping[str, Any]) -> dict[str, Any]:
    """Per-metric (old, new, delta) and probes whose status pass flipped, from two recorded run dicts."""
    deltas = {name: (old["summary"].get(name), value,
                     None if value is None or old["summary"].get(name) is None
                     else value - old["summary"][name])
              for name, value in new["summary"].items()}

    def ok(run: Mapping[str, Any]) -> dict[str, bool]:
        return {o["probe_id"]: o["status"] == o["expected_status"] for o in run["outcomes"]}
    before, after = ok(old), ok(new)
    shared = [pid for pid in after if pid in before]
    return {"deltas": deltas,
            "pass_to_fail": [pid for pid in shared if before[pid] and not after[pid]],
            "fail_to_pass": [pid for pid in shared if not before[pid] and after[pid]],
            "new": [pid for pid in after if pid not in before],
            "removed": [pid for pid in before if pid not in after]}
