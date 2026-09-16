"""Run one probe through a query core and pair the checker's verdict with an observed block."""
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol

from swiss_grounding.evals.checker import check
from swiss_grounding.evals.probe_models import Observed, ObservedCitation, Probe
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.retrieval.models import QueryRequest, QueryResponse


class QueryCoreLike(Protocol):
    tree: LocationTree

    def query(self, request: QueryRequest) -> QueryResponse:
        """Run a query and return the response."""


@dataclass(frozen=True)
class ProbeResult:
    probe: Probe
    response: QueryResponse
    failures: tuple[str, ...]
    observed: Observed

    @property
    def passed(self) -> bool:
        return not self.failures


def to_request(probe: Probe) -> QueryRequest:
    return QueryRequest(
        question=probe.question, location=probe.location, categories=probe.categories,
        as_of=probe.as_of, limit=probe.limit,
    )


def _observed(resp: QueryResponse, failures: tuple[str, ...], git_commit: str | None) -> Observed:
    return Observed(
        recorded_at=datetime.now(UTC), git_commit=git_commit, status=resp.status,
        resolved_id=resp.resolved_location_id, method=resp.resolution_method,
        alternatives=resp.alternatives, message=resp.message,
        citations=tuple(
            ObservedCitation(source=c.source_id, extent=c.extent_id, url=c.url,
                             authority=c.authority, event_date=c.event_date)
            for c in resp.citations
        ),
        failures=failures,
    )


def run_probe(probe: Probe, core: QueryCoreLike, today: date, git_commit: str | None) -> ProbeResult:
    """Query, check, and record. A probe's as_of stands in for today so calendar rules follow it."""
    resp = core.query(to_request(probe))
    failures = check(probe, resp, core.tree, probe.as_of or today)
    return ProbeResult(probe=probe, response=resp, failures=failures,
                       observed=_observed(resp, failures, git_commit))
