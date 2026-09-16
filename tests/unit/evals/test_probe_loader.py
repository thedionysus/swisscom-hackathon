from pathlib import Path

import pytest

from swiss_grounding.evals.probe_loader import PROBE_DIR, load_all_probes, load_probe_file

MINIMAL = """
tier: city
probes:
  - id: city-001
    question: When is the next cardboard collection?
    location: "8004"
    categories: [waste]
    kind: structural
    failure_class: silent_under_coverage
    status: red
    expect:
      status: results
      resolved: {id: CH-ZH-261-K4}
      must_exclude:
        - {source: open_erz}
      coverage_empty: [CH-ZH-261-K4]
"""


def test_load_probe_file(tmp_path: Path):
    path = tmp_path / "city.yaml"
    path.write_text(MINIMAL)
    pf = load_probe_file(path)
    assert pf.tier == "city"
    assert pf.probes[0].location == "8004"


def test_load_all_probes_reads_every_yaml_in_dir(tmp_path: Path):
    (tmp_path / "city.yaml").write_text(MINIMAL)
    (tmp_path / "communes.yaml").write_text(
        MINIMAL.replace("tier: city", "tier: communes").replace("city-001", "com-001")
    )
    probes = load_all_probes(tmp_path)
    assert sorted(p.id for _, p in probes) == ["city-001", "com-001"]
    assert {t for t, _ in probes} == {"city", "communes"}


def test_load_all_probes_rejects_ids_duplicated_across_files(tmp_path: Path):
    (tmp_path / "a.yaml").write_text(MINIMAL)
    (tmp_path / "b.yaml").write_text(MINIMAL.replace("tier: city", "tier: communes"))
    with pytest.raises(ValueError, match="city-001"):
        load_all_probes(tmp_path)


def test_load_probe_file_rejects_non_mapping(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text("- just\n- a list\n")
    with pytest.raises(ValueError, match="mapping"):
        load_probe_file(path)


def test_default_probe_dir_is_repo_evals_probes():
    assert PROBE_DIR.name == "probes"
    assert PROBE_DIR.parent.name == "evals"
    assert (PROBE_DIR.parent.parent / "pyproject.toml").exists()
