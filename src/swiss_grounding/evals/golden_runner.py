"""Run the golden set against the search service and summarise against the thresholds."""
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from swiss_grounding.evals.golden_models import GoldenProbe, GoldenSet
from swiss_grounding.evals.metrics import mean, ndcg_at_k, precision_at_k, recall_at_k
from swiss_grounding.evals.stats import hit_at_k, mrr_at_k
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.models import Citation, PlaceResult, SearchRequest
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
    language: str = ""
    area: str = ""
    level: str = ""
    canton: str | None = None
    hit1: float | None = None
    mrr: float | None = None
    leakage: float | None = None
    lang_match: bool | None = None
    latency_s: float | None = None
    extents: tuple[str, ...] = ()
    location_ids: tuple[str | None, ...] = ()


@dataclass(frozen=True)
class GoldenReport:
    version: str
    split: str
    outcomes: tuple[ProbeOutcome, ...]
    summary: dict[str, float | None]


def leakage(extents_per_place: Sequence[Sequence[str]], paths_per_place: Sequence[Sequence[str]]) -> float | None:
    """Share of cited extents off their place's path (the place, its ancestors, CH)."""
    pairs = [(e, path) for extents, path in zip(extents_per_place, paths_per_place, strict=True) for e in extents]
    return sum(1 for e, path in pairs if e not in path) / len(pairs) if pairs else None


def _path(tree: LocationTree | None, location_id: str | None) -> tuple[str, ...] | None:
    if tree is None or location_id is None or location_id not in tree.by_id:
        return None
    return tree.path(location_id)


def _canton(tree: LocationTree | None, places: Sequence[PlaceResult]) -> str | None:
    path = _path(tree, places[0].location_id) if places else None
    return path[1] if path and len(path) > 1 else None


def _leakage(tree: LocationTree | None, places: Sequence[PlaceResult]) -> float | None:
    paths = [_path(tree, p.location_id) for p in places]
    if not places or any(p is None for p in paths):
        return None
    return leakage([[c.extent_id for c in p.citations[:K]] for p in places], [p or () for p in paths])


def _run_one(service: SearchService, probe: GoldenProbe, labels: Labels) -> ProbeOutcome:
    """Metrics per place, then averaged: a two-place probe must not let one place fill the top 5."""
    as_of = date.fromisoformat(probe.as_of) if probe.as_of else None
    started = time.perf_counter()
    resp = service.search(SearchRequest(probe.question, probe.locations, {}, as_of, 10))
    latency = time.perf_counter() - started
    tree = getattr(service, "tree", None)
    per_place = [tuple(citation_key(c) for c in p.citations) for p in resp.places]
    top = tuple(k for keys in per_place for k in keys[:K])
    status_ok = resp.status if not probe.expect.place_statuses else ",".join(p.status for p in resp.places)
    expected = probe.expect.status if not probe.expect.place_statuses else ",".join(probe.expect.place_statuses)
    first = next((p.citations[0] for p in resp.places if p.citations), None)
    base = {"language": probe.language, "area": probe.area, "level": probe.level, "latency_s": latency,
                "canton": _canton(tree, resp.places) if probe.locations else None,
                "extents": tuple(c.extent_id for p in resp.places for c in p.citations[:K]),
                "location_ids": tuple(p.location_id for p in resp.places)}
    if probe.expect.status != "results":
        return ProbeOutcome(probe.id, expected, status_ok, top, None, None, None, **base)
    judged = [[labels.get((probe.id, k)) for k in keys] for keys in per_place]
    return ProbeOutcome(probe.id, expected, status_ok, top,
                        recall_at_k(top, probe.expect.sources, len(top)),
                        mean([precision_at_k(j, K) for j in judged]),
                        mean([ndcg_at_k(j, K) for j in judged]),
                        hit1=mean([hit_at_k(keys, probe.expect.sources, 1) for keys in per_place]) or 0.0,
                        mrr=mean([mrr_at_k(keys, probe.expect.sources, K) for keys in per_place]) or 0.0,
                        leakage=_leakage(tree, resp.places) if probe.locations else None,
                        lang_match=None if first is None else first.language == probe.language, **base)


def run_golden(service: SearchService, golden: GoldenSet, *, labels: Labels, split: str) -> GoldenReport:
    from swiss_grounding.evals.golden_analysis import summary_values

    probes = [p for p in golden.probes if p.tool == "swiss_search" and split in ("all", p.split)]
    outcomes = tuple(_run_one(service, p, labels) for p in probes)
    return GoldenReport(golden.version, split, outcomes, summary_values(outcomes))
