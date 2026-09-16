from datetime import UTC, date, datetime

from swiss_grounding.evals.checker import check
from swiss_grounding.evals.probe_models import EvidenceRule, Expectation, Probe, ResolvedExpectation
from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.retrieval.models import Citation, QueryResponse

TODAY = date(2026, 9, 16)


def _loc(node_id, parent, level, name, bfs=None):
    return Location(id=node_id, parent_id=parent, level=level, bfs_id=bfs, lindas_uri=None,
                    names={"en": name}, aliases=())


def _tree() -> LocationTree:
    return LocationTree.from_locations([
        _loc("CH", None, Level.COUNTRY, "Switzerland"),
        _loc("CH-ZH", "CH", Level.CANTON, "Zurich", 1),
        _loc("CH-ZH-261", "CH-ZH", Level.MUNICIPALITY, "Zurich", 261),
        _loc("CH-ZH-261-K3", "CH-ZH-261", Level.NEIGHBORHOOD, "District 3"),
        _loc("CH-ZH-261-K4", "CH-ZH-261", Level.NEIGHBORHOOD, "District 4"),
    ])


def _cit(source="fedlex", extent="CH", url="https://www.fedlex.admin.ch/eli/cc/2008/414/de",
         authority="federal_law", event_date=None) -> Citation:
    return Citation(
        chunk_id=1, document_id=1, source_id=source, title_en="t", title_original="t", url=url,
        anchor=None, identifier=None, snippet_en="s", snippet_original="s", language="de",
        heading_path="", extent_id=extent, extent_label=extent, authority=authority,
        categories=("dogs",), valid_from=None, retrieved_at=datetime(2026, 9, 14, tzinfo=UTC),
        license=None, score=1.0, event_date=event_date,
    )


def _probe(**expect) -> Probe:
    return Probe(id="x", question="q", location="8004", kind="structural", failure_class="none",
                 status="green", expect=Expectation(**expect))


def _resp(**overrides) -> QueryResponse:
    base = {"status": "results", "resolved_location_id": "CH-ZH-261-K4",
            "resolution_method": "alias", "citations": (_cit(),)}
    return QueryResponse(**{**base, **overrides})


def test_passes_when_everything_matches():
    probe = _probe(status="results", resolved=ResolvedExpectation(id="CH-ZH-261-K4"),
                   must_include=(EvidenceRule(source="fedlex"),))
    assert check(probe, _resp(), _tree(), TODAY) == ()


def test_status_mismatch():
    probe = _probe(status="needs_location")
    assert check(probe, _resp(), _tree(), TODAY) == ("status: expected needs_location, got results",)


def test_resolved_id_mismatch():
    probe = _probe(status="results", resolved=ResolvedExpectation(id="CH-ZH-261-K3"))
    assert "resolved: expected CH-ZH-261-K3, got CH-ZH-261-K4" in check(probe, _resp(), _tree(), TODAY)


def test_resolved_by_label_level_parent_uses_tree():
    probe = _probe(status="results", resolved=ResolvedExpectation(
        label="District 4", level="neighborhood", parent="CH-ZH-261"))
    assert check(probe, _resp(), _tree(), TODAY) == ()
    wrong = _probe(status="results", resolved=ResolvedExpectation(
        label="Winterthur", level="municipality", parent="CH-ZH"))
    failures = check(wrong, _resp(), _tree(), TODAY)
    assert any(f.startswith("resolved: expected Winterthur (municipality under CH-ZH)") for f in failures)


def test_resolved_by_label_when_response_has_no_node():
    probe = _probe(status="results", resolved=ResolvedExpectation(label="Winterthur", level="municipality", parent="CH-ZH"))
    resp = _resp(resolved_location_id=None)
    assert check(probe, resp, _tree(), TODAY) == ("resolved: expected Winterthur (municipality under CH-ZH), got None",)


def test_method_and_alternatives():
    probe = _probe(status="results", method="geoadmin", alternatives_include=("CH-ZH",))
    failures = check(probe, _resp(), _tree(), TODAY)
    assert "method: expected geoadmin, got alias" in failures
    assert "alternatives: CH-ZH missing; none returned" in failures


def test_must_include_reports_missing_rule():
    probe = _probe(status="results", must_include=(EvidenceRule(source="zh_ch", url_contains="hunde"),))
    assert check(probe, _resp(), _tree(), TODAY) == (
        "must_include: no citation matched source=zh_ch url_contains=hunde",)


def test_must_exclude_reports_matching_citation():
    probe = _probe(status="results", must_exclude=(EvidenceRule(source="fedlex"),))
    assert check(probe, _resp(), _tree(), TODAY) == (
        "must_exclude: citation matched source=fedlex (https://www.fedlex.admin.ch/eli/cc/2008/414/de)",)


def test_off_path_extent_rule():
    probe = _probe(status="results", must_exclude=(EvidenceRule(extent="off_path"),))
    leak = _resp(citations=(_cit(source="open_erz", extent="CH-ZH-261-K3", url="https://openerz.metaodi.ch/x"),))
    assert check(probe, leak, _tree(), TODAY) == (
        "must_exclude: citation matched extent=off_path (https://openerz.metaodi.ch/x)",)
    assert check(probe, _resp(), _tree(), TODAY) == ()


def test_first_extent_authority_url():
    probe = _probe(status="results", first_extent="CH-ZH", first_authority="official_info",
                   first_url_contains="zh.ch")
    failures = check(probe, _resp(), _tree(), TODAY)
    assert "first_extent: expected CH-ZH, got CH" in failures
    assert "first_authority: expected official_info, got federal_law" in failures
    assert "first_url_contains: 'zh.ch' not in https://www.fedlex.admin.ch/eli/cc/2008/414/de" in failures


def test_first_rules_with_no_citations():
    probe = _probe(status="results", first_extent="CH-ZH")
    assert check(probe, _resp(citations=()), _tree(), TODAY) == ("first: no citations returned",)


def test_first_event_nearest_future():
    probe = _probe(status="results", first_event="nearest_future")
    good = _resp(citations=(_cit(source="open_erz", event_date=date(2026, 9, 17)),
                            _cit(source="open_erz", event_date=date(2026, 12, 31))))
    assert check(probe, good, _tree(), TODAY) == ()
    bad = _resp(citations=(_cit(source="open_erz", event_date=date(2026, 12, 31)),
                           _cit(source="open_erz", event_date=date(2026, 9, 17))))
    assert check(probe, bad, _tree(), TODAY) == (
        "first_event: expected nearest future 2026-09-17, first citation has 2026-12-31",)
    past = _resp(citations=(_cit(source="open_erz", event_date=date(2026, 9, 10)),
                            _cit(source="open_erz", event_date=date(2026, 12, 31))))
    assert check(probe, past, _tree(), TODAY) == (
        "first_event: first citation 2026-09-10 is before today 2026-09-16",)
    dateless = _resp(citations=(_cit(),))
    assert check(probe, dateless, _tree(), TODAY) == ("first_event: first citation carries no event_date",)


def test_first_event_with_only_past_events():
    probe = _probe(status="results", first_event="nearest_future")
    resp = _resp(citations=(_cit(source="open_erz", event_date=date(2026, 9, 10)),))
    assert check(probe, resp, _tree(), TODAY) == (
        "first_event: no citation carries a future event date (nearest is 2026-09-10)",)


def test_coverage_signal_missing_is_a_failure():
    probe = _probe(status="results", coverage_empty=("CH-ZH-261-K4",), coverage_present=("CH",))
    assert check(probe, _resp(), _tree(), TODAY) == ("coverage: response carries no coverage signal",)


def test_coverage_signal_checked_when_present():
    probe = _probe(status="results", coverage_empty=("CH-ZH-261-K4",), coverage_present=("CH", "CH-ZH"))
    resp = _resp()
    # QueryResponse is frozen; coverage is a future field, so attach it the way the fix pass will.
    object.__setattr__(resp, "coverage", (
        {"extent_id": "CH", "documents": 3}, {"extent_id": "CH-ZH-261-K4", "documents": 2}))
    assert check(probe, resp, _tree(), TODAY) == (
        "coverage: expected CH-ZH-261-K4 empty, has 2 documents",
        "coverage: CH-ZH not listed in signal",
    )


def test_coverage_empty_extent_not_listed():
    probe = _probe(status="results", coverage_empty=("CH-ZH-261-K4",))
    resp = _resp()
    object.__setattr__(resp, "coverage", ({"extent_id": "CH", "documents": 3},))
    assert check(probe, resp, _tree(), TODAY) == ("coverage: CH-ZH-261-K4 not listed in signal",)


def test_coverage_rows_of_unexpected_shape_do_not_crash():
    probe = _probe(status="results", coverage_empty=("CH-ZH-261-K4",))
    resp = _resp()
    object.__setattr__(resp, "coverage", ({"extent": "CH", "docs": 3},))
    assert check(probe, resp, _tree(), TODAY) == (
        "coverage: signal rows are not shaped {extent_id, documents}",)


def test_coverage_rows_as_objects_are_accepted():
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class CoverageRow:
        extent_id: str
        documents: int

    probe = _probe(status="results", coverage_empty=("CH-ZH-261-K4",), coverage_present=("CH",))
    resp = _resp()
    object.__setattr__(resp, "coverage", (
        CoverageRow(extent_id="CH", documents=3), CoverageRow(extent_id="CH-ZH-261-K4", documents=0)))
    assert check(probe, resp, _tree(), TODAY) == ()


def test_message_contains():
    probe = _probe(status="needs_location", message_contains="Atlantis")
    resp = QueryResponse(status="needs_location", message="Could not resolve location 'Nowhere'.")
    assert check(probe, resp, _tree(), TODAY) == (
        "message: 'Atlantis' not in \"Could not resolve location 'Nowhere'.\"",)


def test_off_path_with_unresolved_location():
    probe = _probe(status="results", must_exclude=(EvidenceRule(extent="off_path"),))
    resp = _resp(resolved_location_id=None)
    assert check(probe, resp, _tree(), TODAY) == (
        "off_path: response resolved no location, so no extent path to judge against",)


def test_must_include_off_path_positive_direction():
    probe = _probe(status="results", must_include=(EvidenceRule(extent="off_path"),))
    leak = _resp(citations=(_cit(source="open_erz", extent="CH-ZH-261-K3", url="https://openerz.metaodi.ch/x"),))
    assert check(probe, leak, _tree(), TODAY) == ()
    assert check(probe, _resp(), _tree(), TODAY) == (
        "must_include: no citation matched extent=off_path",)


def test_resolved_level_only_mismatch():
    probe = _probe(status="results", resolved=ResolvedExpectation(
        label="District 4", level="municipality", parent="CH-ZH-261"))
    failures = check(probe, _resp(), _tree(), TODAY)
    assert any(f.startswith(
        "resolved: expected District 4 (municipality under CH-ZH-261), got CH-ZH-261-K4") for f in failures)


def test_multiple_citations_matching_one_exclude_rule():
    probe = _probe(status="results", must_exclude=(EvidenceRule(source="fedlex"),))
    resp = _resp(citations=(
        _cit(source="fedlex", url="https://www.fedlex.admin.ch/eli/cc/2008/414/de"),
        _cit(source="fedlex", url="https://www.fedlex.admin.ch/eli/cc/2009/1/de"),
    ))
    assert check(probe, resp, _tree(), TODAY) == (
        "must_exclude: citation matched source=fedlex (https://www.fedlex.admin.ch/eli/cc/2008/414/de)",
        "must_exclude: citation matched source=fedlex (https://www.fedlex.admin.ch/eli/cc/2009/1/de)",
    )


def test_coverage_resolved_sentinel_names_the_resolved_node():
    probe = _probe(status="results", coverage_empty=("resolved",), coverage_present=("CH",))
    resp = _resp()
    object.__setattr__(resp, "coverage", (
        {"extent_id": "CH", "documents": 3}, {"extent_id": "CH-ZH-261-K4", "documents": 0}))
    assert check(probe, resp, _tree(), TODAY) == ()
    unresolved = _resp(resolved_location_id=None)
    object.__setattr__(unresolved, "coverage", ({"extent_id": "CH", "documents": 3},))
    assert check(probe, unresolved, _tree(), TODAY) == (
        "coverage: no resolved location to check emptiness for",)
