from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from swiss_grounding.evals.probe_loader import load_probe_file
from swiss_grounding.evals.probe_models import Observed, ObservedCitation
from swiss_grounding.evals.recorder import record_observed

SRC = """
tier: city
probes:
  - id: city-001
    question: q
    location: "8003"
    kind: structural
    failure_class: none
    status: green
    expect:
      status: results
  - id: city-002
    question: q2
    kind: structural
    failure_class: none
    status: green
    expect:
      status: needs_location
"""


def _observed(**overrides) -> Observed:
    base = {"recorded_at": datetime(2026, 9, 16, 12, 0, tzinfo=UTC), "git_commit": "abc",
            "status": "results", "resolved_id": "CH-ZH-261-K3", "method": "alias",
            "citations": (ObservedCitation(source="open_erz", extent="CH-ZH-261-K3",
                                           url="https://x", authority="official_info"),),
            "failures": ()}
    return Observed(**{**base, **overrides})


def test_record_observed_writes_block_for_matching_probe_only(tmp_path: Path):
    path = tmp_path / "city.yaml"
    path.write_text(SRC)
    obs = _observed()
    record_observed(path, {"city-001": obs})
    pf = load_probe_file(path)
    assert pf.probes[0].observed == obs
    assert pf.probes[1].observed is None
    raw = yaml.safe_load(path.read_text())
    assert raw["probes"][0]["observed"]["resolved_id"] == "CH-ZH-261-K3"
    assert raw["probes"][0]["expect"] == {"status": "results"}
    assert raw["probes"][0]["location"] == "8003"


def test_record_observed_replaces_previous_block(tmp_path: Path):
    path = tmp_path / "city.yaml"
    path.write_text(SRC)
    first = _observed(failures=("a",))
    second = _observed(recorded_at=datetime(2026, 9, 17, tzinfo=UTC), failures=())
    record_observed(path, {"city-001": first})
    record_observed(path, {"city-001": second})
    assert load_probe_file(path).probes[0].observed == second


def test_record_observed_keeps_key_order_and_unicode(tmp_path: Path):
    path = tmp_path / "city.yaml"
    path.write_text(SRC.replace("question: q2", "question: Wann wird Karton in Dübendorf abgeholt?"))
    record_observed(path, {"city-002": _observed()})
    text = path.read_text()
    assert "Dübendorf" in text
    assert text.index("tier:") < text.index("probes:")
    assert text.index("id: city-002") < text.index("observed:")


def test_record_observed_rejects_unknown_probe_id(tmp_path: Path):
    path = tmp_path / "city.yaml"
    path.write_text(SRC)
    with pytest.raises(ValueError, match="city-999"):
        record_observed(path, {"city-999": _observed()})
    assert load_probe_file(path).probes[0].observed is None


def test_record_observed_leaves_file_untouched_when_result_would_be_invalid(tmp_path: Path):
    path = tmp_path / "city.yaml"
    path.write_text(SRC)
    before = path.read_text()
    bad = _observed().model_copy(update={"status": 12345})
    with pytest.raises(ValueError):
        record_observed(path, {"city-001": bad})
    assert path.read_text() == before
