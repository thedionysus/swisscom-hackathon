import pytest
from pydantic import ValidationError

from swiss_grounding.evals.golden_models import GoldenSet

GOOD = {"version": "2026-09-24.1", "probes": [{
    "id": "g-rm-scuol-holidays", "question": "Cura èn las vacanzas d'atun 2026 per la scola da Scuol?",
    "language": "rm", "area": "school_holidays", "level": "municipal", "split": "dev",
    "expect": {"status": "results", "sources": ["scuol"], "key_fact": "Herbstferien 2026 Scuol"}}]}


def test_valid_golden_set():
    assert GoldenSet.model_validate(GOOD).probes[0].locations == ()


def test_results_probe_needs_a_source_and_a_key_fact():
    bad = {**GOOD, "probes": [{**GOOD["probes"][0], "expect": {"status": "results"}}]}
    with pytest.raises(ValidationError, match="sources"):
        GoldenSet.model_validate(bad)


def test_ids_are_unique():
    with pytest.raises(ValidationError, match="duplicate"):
        GoldenSet.model_validate({**GOOD, "probes": GOOD["probes"] * 2})


def _probe(**over):
    return {**GOOD["probes"][0], **over}


def test_tool_probe_takes_args_and_exact_checks():
    probe = _probe(id="t-premium", tool="swiss_premium", args={"municipality": "Lugano", "age": 30},
                   expect={"status": "results", "contains": ["Lugano"], "value_path": "premiums.0.premium_chf",
                           "value": 449.9, "tolerance": 0.5})
    parsed = GoldenSet.model_validate({**GOOD, "probes": [probe]}).probes[0]
    assert parsed.args["age"] == 30 and parsed.expect.value == 449.9


def test_zbern_tools_are_accepted_and_unknown_tools_rejected():
    ok = _probe(tool="zbern_search_person", expect={"status": "results", "nonempty": ["results"]})
    assert GoldenSet.model_validate({**GOOD, "probes": [ok]}).probes[0].tool == "zbern_search_person"
    with pytest.raises(ValidationError, match="tool"):
        GoldenSet.model_validate({**GOOD, "probes": [_probe(tool="rm_rf")]})


def test_tool_results_probe_needs_a_check_not_sources():
    with pytest.raises(ValidationError, match="check"):
        GoldenSet.model_validate({**GOOD, "probes": [_probe(tool="swiss_scope", expect={"status": "results"})]})


def test_value_needs_a_path():
    bad = _probe(tool="swiss_reference_rate", expect={"status": "results", "value": 1.25})
    with pytest.raises(ValidationError, match="value_path"):
        GoldenSet.model_validate({**GOOD, "probes": [bad]})


def test_group_is_optional():
    assert GoldenSet.model_validate({**GOOD, "probes": [_probe(group="marriage-age")]}).probes[0].group == "marriage-age"
