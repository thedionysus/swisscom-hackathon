"""Stability of search under deterministic question perturbations. No LLM spend."""
import zlib
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from swiss_grounding.evals.golden_models import SEARCH_TOOL, GoldenSet
from swiss_grounding.evals.metrics import mean, recall_at_k
from swiss_grounding.evals.perturb import perturbations
from swiss_grounding.serving.models import SearchResponse

K = 5
METRICS = ("status_agreement", "top1_agreement", "jaccard@5", "recall@5")


@dataclass(frozen=True)
class Hit:
    status: str
    keys: tuple[str, ...]   # citation keys (url#anchor), the top K of each place in order


Search = Callable[[str, tuple[str, ...]], Hit]


@dataclass(frozen=True)
class Stability:
    status_agrees: bool
    top1_agrees: bool
    jaccard: float
    recall: float


@dataclass(frozen=True)
class RobustnessReport:
    probes: int
    baseline_recall: float | None
    per_perturbation: dict[str, dict[str, float | None]]
    overall: dict[str, float | None]


def hit_from_response(resp: SearchResponse) -> Hit:
    keys = tuple(f"{c.url}#{c.anchor}" if c.anchor else c.url for p in resp.places for c in p.citations[:K])
    return Hit(resp.status, keys)


def compare(base: Hit, variant: Hit, expected: Sequence[str]) -> Stability:
    a, b = set(base.keys[:K]), set(variant.keys[:K])
    return Stability(base.status == variant.status,
                     base.keys[:1] == variant.keys[:1],
                     len(a & b) / len(a | b) if a | b else 1.0,
                     recall_at_k(variant.keys, expected, len(variant.keys)))


def _means(rows: Sequence[Stability]) -> dict[str, float | None]:
    return {"status_agreement": mean([float(r.status_agrees) for r in rows]),
            "top1_agreement": mean([float(r.top1_agrees) for r in rows]),
            "jaccard@5": mean([r.jaccard for r in rows]),
            "recall@5": mean([r.recall for r in rows])}


def run_robustness(golden: GoldenSet, search: Search, *, split: str, seed: int) -> RobustnessReport:
    probes = [p for p in golden.probes if p.tool == SEARCH_TOOL and p.expect.status == "results"
              and split in ("all", p.split)]
    by_name: dict[str, list[Stability]] = defaultdict(list)
    baseline = []
    for p in probes:
        base = search(p.question, p.locations)
        baseline.append(recall_at_k(base.keys, p.expect.sources, len(base.keys)))
        variants = perturbations(p.question, p.language, seed=seed + zlib.crc32(p.id.encode()))
        for name, question in variants.items():
            by_name[name].append(compare(base, search(question, p.locations), p.expect.sources))
    return RobustnessReport(len(probes), mean(baseline), {n: _means(rows) for n, rows in sorted(by_name.items())},
                            _means([r for rows in by_name.values() for r in rows]))
