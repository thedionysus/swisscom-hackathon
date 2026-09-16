from datetime import date

import pytest
from pydantic import ValidationError

from swiss_grounding.evals.probe_models import (
    EvidenceRule,
    Expectation,
    Observed,
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


def test_resolved_expectation_requires_id_or_label():
    with pytest.raises(ValidationError):
        ResolvedExpectation(level="municipality")


def test_resolved_expectation_roundtrips_label_level_parent():
    r = ResolvedExpectation(label="Winterthur", level="municipality", parent="CH-ZH")
    assert r.label == "Winterthur"
    assert r.level == "municipality"
    assert r.parent == "CH-ZH"


def test_observed_block_roundtrips_with_citation_and_event_date():
    obs = Observed.model_validate(
        {
            "recorded_at": "2026-09-16T12:00:00+00:00",
            "status": "results",
            "citations": [
                {
                    "source": "open_erz",
                    "extent": "CH-ZH-261-K3",
                    "url": "https://x",
                    "authority": "official_info",
                    "event_date": "2026-09-17",
                }
            ],
            "failures": [],
        }
    )
    assert obs.citations[0].event_date == date(2026, 9, 17)
    assert obs.recorded_at.tzinfo is not None


def test_evidence_rule_rejects_empty_string_selectors():
    with pytest.raises(ValidationError):
        EvidenceRule(url_contains="")


def test_unknown_category_rejected():
    with pytest.raises(ValidationError):
        ProbeFile.model_validate({"tier": "city", "probes": [_probe(categories=["wast"])]})


def test_limit_must_be_positive():
    with pytest.raises(ValidationError):
        ProbeFile.model_validate({"tier": "city", "probes": [_probe(limit=0)]})


def test_empty_probe_file_rejected():
    with pytest.raises(ValidationError):
        ProbeFile.model_validate({"tier": "city", "probes": []})


def test_expectation_rejects_empty_first_and_message_selectors():
    with pytest.raises(ValidationError):
        Expectation(status="results", first_extent="")
    with pytest.raises(ValidationError):
        Expectation(status="results", message_contains="")
