from swiss_grounding.evals.golden_models import GoldenProbe, GoldenSet
from swiss_grounding.evals.tool_checks import check_tool, run_tools


def probe(tool="swiss_reference_rate", args=None, **expect) -> GoldenProbe:
    return GoldenProbe.model_validate({
        "id": f"t-{tool}", "question": "tool probe", "language": "de", "area": "housing", "level": "federal",
        "split": "dev", "tool": tool, "args": args or {}, "expect": {"status": "results", **expect}})


def test_value_within_tolerance_passes():
    p = probe(value_path="rate_percent", value=1.25, tolerance=0.001)
    assert check_tool(p, {"status": "results", "rate_percent": 1.25}).passed


def test_value_outside_tolerance_fails_with_a_reason():
    out = check_tool(probe(value_path="premiums.0.premium_chf", value=449.9),
                     {"status": "results", "premiums": [{"premium_chf": 451.0}]})
    assert not out.passed and "451" in out.reason


def test_missing_path_fails():
    assert not check_tool(probe(value_path="rate_percent", value=1.25), {"status": "results"}).passed


def test_contains_is_checked_against_the_json_text():
    p = probe(contains=["Jositsch", "3891"])
    assert check_tool(p, {"status": "results", "results": [{"lastName": "Jositsch", "personNumber": 3891}]}).passed
    failed = check_tool(p, {"status": "results", "results": []})
    assert not failed.passed and "Jositsch" in failed.reason


def test_nonempty_paths():
    p = probe(nonempty=["connections"])
    assert check_tool(p, {"status": "results", "connections": [{"x": 1}]}).passed
    assert not check_tool(p, {"status": "results", "connections": []}).passed


def test_status_mismatch_fails_and_missing_status_counts_as_results():
    assert not check_tool(probe(contains=["a"]), {"status": "source_unavailable", "a": 1}).passed
    assert check_tool(probe(contains=["a"]), {"a": 1}).passed


def test_unlisted_tool_is_skipped():
    out = check_tool(probe(tool="zbern_get_person", contains=["x"]), None)
    assert out.skipped and not out.passed and "zbern" in out.reason


def test_run_tools_calls_only_non_search_probes_and_summarises():
    search = GoldenProbe.model_validate({
        "id": "s-1", "question": "what?", "language": "de", "area": "law", "level": "federal", "split": "dev",
        "expect": {"status": "results", "sources": ["x"], "key_fact": "y"}})
    golden = GoldenSet(version="v", probes=(search, probe(value_path="rate_percent", value=1.25),
                                            probe(tool="zbern_get_coverage", contains=["x"])))
    seen = []

    def caller(calls):
        seen.extend(calls)
        return frozenset({"swiss_reference_rate"}), ({"rate_percent": 1.25}, None)
    report = run_tools(golden, caller)
    assert [name for name, _ in seen] == ["swiss_reference_rate", "zbern_get_coverage"]
    assert report.summary == {"passed": 1, "failed": 0, "skipped": 1}
