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
