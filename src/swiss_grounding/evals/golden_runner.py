"""Run the golden set against the search service and summarise against the thresholds."""
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from swiss_grounding.evals.golden_models import GoldenProbe, GoldenSet
from swiss_grounding.evals.metrics import mean, ndcg_at_k, precision_at_k, recall_at_k
from swiss_grounding.serving.models import Citation, SearchRequest
from swiss_grounding.serving.search_service import SearchService

K = 5
Labels = Mapping[tuple[str, str], bool]


def citation_key(c: Citation) -> str:
    return f"{c.url}#{c.anchor}" if c.anchor else c.url


@dataclass(frozen=True)
class ProbeOutcome:
    probe_id: str
    expected_status: str
    status: str
    keys: tuple[str, ...]
    recall: float | None
    precision: float | None
    ndcg: float | None


@dataclass(frozen=True)
class GoldenReport:
    version: str
    split: str
    outcomes: tuple[ProbeOutcome, ...]
    summary: dict[str, float | None]


def _run_one(service: SearchService, probe: GoldenProbe, labels: Labels) -> ProbeOutcome:
    """Metrics per place, then averaged: a two-place probe must not let one place fill the top 5."""
    as_of = date.fromisoformat(probe.as_of) if probe.as_of else None
    resp = service.search(SearchRequest(probe.question, probe.locations, {}, as_of, 10))
    per_place = [tuple(citation_key(c) for c in p.citations) for p in resp.places]
    top = tuple(k for keys in per_place for k in keys[:K])
    status_ok = resp.status if not probe.expect.place_statuses else ",".join(p.status for p in resp.places)
    expected = probe.expect.status if not probe.expect.place_statuses else ",".join(probe.expect.place_statuses)
    if probe.expect.status != "results":
        return ProbeOutcome(probe.id, expected, status_ok, top, None, None, None)
    judged = [[labels.get((probe.id, k)) for k in keys] for keys in per_place]
    return ProbeOutcome(probe.id, expected, status_ok, top,
                        recall_at_k(top, probe.expect.sources, len(top)),
                        mean([precision_at_k(j, K) for j in judged]),
                        mean([ndcg_at_k(j, K) for j in judged]))


def run_golden(service: SearchService, golden: GoldenSet, *, labels: Labels, split: str) -> GoldenReport:
    probes = [p for p in golden.probes if p.tool == "swiss_search" and split in ("all", p.split)]
    outcomes = tuple(_run_one(service, p, labels) for p in probes)
    summary = {
        "status_accuracy": mean([1.0 if o.status == o.expected_status else 0.0 for o in outcomes]),
        "recall@5": mean([o.recall for o in outcomes]),
        "precision@5": mean([o.precision for o in outcomes]),
        "ndcg@5": mean([o.ndcg for o in outcomes]),
    }
    return GoldenReport(golden.version, split, outcomes, summary)
