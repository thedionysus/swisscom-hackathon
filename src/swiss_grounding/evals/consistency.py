"""Cross-language consistency: probes sharing a `group` ask the same thing in several languages."""
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from swiss_grounding.evals.golden_models import SEARCH_TOOL, GoldenSet
from swiss_grounding.evals.metrics import mean


@dataclass(frozen=True)
class Answer:
    status: str
    top: str | None   # the top citation's language-independent key: translation group (plus anchor)


Ask = Callable[[str, tuple[str, ...]], Answer]


@dataclass(frozen=True)
class GroupOutcome:
    group: str
    answers: tuple[tuple[str, str, Answer], ...]   # (probe id, language, answer)
    status_agrees: bool
    top_agrees: bool


@dataclass(frozen=True)
class ConsistencyReport:
    groups: tuple[GroupOutcome, ...]
    summary: dict[str, float | int | None]


def run_consistency(golden: GoldenSet, ask: Ask, *, split: str) -> ConsistencyReport:
    grouped = defaultdict(list)
    for p in golden.probes:
        if p.group and p.tool == SEARCH_TOOL and split in ("all", p.split):
            grouped[p.group].append(p)
    outcomes = []
    for name, probes in sorted(grouped.items()):
        if len(probes) < 2:
            continue
        answers = tuple((p.id, p.language, ask(p.question, p.locations)) for p in probes)
        tops = {a.top for _, _, a in answers}
        outcomes.append(GroupOutcome(name, answers, len({a.status for _, _, a in answers}) == 1,
                                     len(tops) == 1 and None not in tops))
    summary = {"groups": len(outcomes),
               "status_agreement": mean([float(o.status_agrees) for o in outcomes]),
               "top_citation_agreement": mean([float(o.top_agrees) for o in outcomes])}
    return ConsistencyReport(tuple(outcomes), summary)
