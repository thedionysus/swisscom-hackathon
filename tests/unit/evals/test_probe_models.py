import pytest
from pydantic import ValidationError

from swiss_grounding.evals.probe_models import (
    EvidenceRule,
    Expectation,
    ProbeFile,
    ResolvedExpectation,
)


def _probe(**overrides) -> dict:
    base = {
        "id": "city-001",
        "question": "When is the next cardboard collection?",
        "location": "8004",
        "categories": ["waste"],
        "kind": "structural",
        "failure_class": "silent_under_coverage",
        "status": "red",
        "expect": {
            "status": "results",
            "resolved": {"id": "CH-ZH-261-K4"},
            "must_exclude": [{"source": "open_erz"}],
            "coverage_empty": ["CH-ZH-261-K4"],
        },
    }
    return {**base, **overrides}


def test_probe_file_parses_minimal_probe():
    pf = ProbeFile.model_validate({"tier": "city", "probes": [_probe()]})
    probe = pf.probes[0]
    assert probe.id == "city-001"
    assert probe.limit == 8
    assert probe.judge is False
    assert probe.expect.resolved == ResolvedExpectation(id="CH-ZH-261-K4")
    assert probe.expect.must_exclude == (EvidenceRule(source="open_erz"),)


def test_evidence_rule_needs_at_least_one_selector():
    with pytest.raises(ValidationError):
        EvidenceRule()


def test_resolved_expectation_by_label_and_level():
    r = ResolvedExpectation(label="Winterthur", level="municipality", parent="CH-ZH")
    assert r.id is None


def test_unknown_failure_class_rejected():
    with pytest.raises(ValidationError):
        ProbeFile.model_validate({"tier": "city", "probes": [_probe(failure_class="vibes")]})


def test_duplicate_probe_ids_rejected():
    with pytest.raises(ValidationError):
        ProbeFile.model_validate({"tier": "city", "probes": [_probe(), _probe()]})


def test_extra_keys_rejected():
    with pytest.raises(ValidationError):
        ProbeFile.model_validate({"tier": "city", "probes": [_probe(surprise=1)]})


def test_expectation_defaults_are_empty():
    e = Expectation(status="results")
    assert e.must_include == ()
    assert e.coverage_empty == ()
    assert e.first_event is None
