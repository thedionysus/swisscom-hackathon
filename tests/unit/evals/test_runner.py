from datetime import UTC, date, datetime

from swiss_grounding.evals.probe_models import Expectation, Probe, ResolvedExpectation
from swiss_grounding.evals.runner import ProbeResult, run_probe, to_request
from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.retrieval.models import Citation, QueryRequest, QueryResponse

TODAY = date(2026, 9, 16)


class FakeCore:
    def __init__(self, resp: QueryResponse):
        self.resp = resp
        self.tree = LocationTree.from_locations([
            Location(id="CH", parent_id=None, level=Level.COUNTRY, bfs_id=None, lindas_uri=None,
                     names={"en": "Switzerland"}, aliases=()),
        ])
        self.seen: list[QueryRequest] = []

    def query(self, request: QueryRequest) -> QueryResponse:
        self.seen.append(request)
        return self.resp


def _probe(**overrides) -> Probe:
    base = {"id": "p", "question": "q", "location": "Switzerland", "categories": ("dogs",), "limit": 5,
            "kind": "structural", "failure_class": "none", "status": "green",
            "expect": Expectation(status="results", resolved=ResolvedExpectation(id="CH"))}
    return Probe(**{**base, **overrides})


def _cit(event_date=None) -> Citation:
    return Citation(chunk_id=1, document_id=1, source_id="open_erz", title_en="t", title_original="t",
                    url="https://x", anchor=None, identifier=None, snippet_en="s", snippet_original="s",
                    language="en", heading_path="", extent_id="CH", extent_label="CH",
                    authority="official_info", categories=("waste",), valid_from=None,
                    retrieved_at=datetime(2026, 9, 14, tzinfo=UTC), license=None, score=1.0,
                    event_date=event_date)


def test_to_request_maps_probe_fields():
    req = to_request(_probe())
    assert req == QueryRequest(question="q", location="Switzerland", categories=("dogs",), as_of=None, limit=5)


def test_run_probe_builds_result_with_observed():
    core = FakeCore(QueryResponse(status="results", resolved_location_id="CH", resolution_method="alias",
                                  citations=(_cit(),)))
    result = run_probe(_probe(), core, TODAY, git_commit="abc123")
    assert isinstance(result, ProbeResult)
    assert result.passed is True
    assert result.failures == ()
    assert result.observed.resolved_id == "CH"
    assert result.observed.method == "alias"
    assert result.observed.git_commit == "abc123"
    assert result.observed.citations[0].source == "open_erz"
    assert result.observed.citations[0].extent == "CH"
    assert result.observed.recorded_at.tzinfo is not None
    assert core.seen[0].limit == 5


def test_run_probe_records_failures():
    core = FakeCore(QueryResponse(status="needs_location", message="no"))
    result = run_probe(_probe(), core, TODAY, git_commit=None)
    assert result.passed is False
    assert "status: expected results, got needs_location" in result.failures
    assert result.observed.failures == result.failures
    assert result.observed.message == "no"


def test_run_probe_uses_probe_as_of_as_today_when_set():
    core = FakeCore(QueryResponse(status="results", resolved_location_id="CH", resolution_method="alias",
                                  citations=(_cit(event_date=date(2026, 9, 14)),)))
    probe = _probe(as_of=date(2026, 9, 12), expect=Expectation(status="results", first_event="nearest_future"))
    assert run_probe(probe, core, TODAY, git_commit=None).passed is True
    probe_no_as_of = _probe(expect=Expectation(status="results", first_event="nearest_future"))
    assert run_probe(probe_no_as_of, core, TODAY, git_commit=None).passed is False
