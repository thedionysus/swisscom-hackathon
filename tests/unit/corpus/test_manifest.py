import pytest

from swiss_grounding.corpus.manifest import load_manifest, select_sources

MANIFEST = """
version: 1
sources:
  - id: fedlex
    name: Fedlex
    publisher: Federal Chancellery
    authority: federal_law
    level: federal
    extent_id: CH
    connector: fedlex
    tier: 1
    languages: [de, fr, it, en]
    config: {sr_numbers: ["220"]}
  - id: bern_city
    name: Stadt Bern
    publisher: Stadt Bern
    authority: official_info
    level: municipal
    extent_id: CH-BE-351
    connector: html
    tier: 2
    languages: [de, fr]
    config: {start_urls: ["https://www.bern.ch/"], allow_prefixes: ["https://www.bern.ch/"]}
"""


def test_loads_and_selects_by_tier(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST)
    manifest = load_manifest(path)
    assert [s.id for s in select_sources(manifest, tier=1)] == ["fedlex"]
    assert [s.id for s in select_sources(manifest, tier=2)] == ["fedlex", "bern_city"]
    assert [s.id for s in select_sources(manifest, tier=2, source_ids=("bern_city",))] == ["bern_city"]


def test_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST.replace("id: bern_city", "id: fedlex"))
    with pytest.raises(ValueError, match="duplicate"):
        load_manifest(path)


def test_html_source_needs_start_urls(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST.replace('start_urls: ["https://www.bern.ch/"], ', ""))
    with pytest.raises(ValueError, match="start_urls"):
        load_manifest(path)


def test_rejects_unknown_language(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST.replace("[de, fr]", "[de, xx]"))
    with pytest.raises(ValueError):
        load_manifest(path)


def test_rejects_duplicate_languages(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST.replace("[de, fr]", "[de, de]"))
    with pytest.raises(ValueError):
        load_manifest(path)


def test_rejects_invalid_id(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST.replace("id: bern_city", "id: Bern City!"))
    with pytest.raises(ValueError):
        load_manifest(path)


def test_reads_manifest_as_utf8(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_bytes((MANIFEST.replace("Stadt Bern", "Stadt Zürich")).encode("utf-8"))
    manifest = load_manifest(path)
    assert manifest.sources[1].name == "Stadt Zürich"


def test_select_sources_rejects_unknown_source_ids(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST)
    manifest = load_manifest(path)
    with pytest.raises(ValueError, match="unknown_id"):
        select_sources(manifest, tier=2, source_ids=("bern_city", "unknown_id"))


OVERLAP = """
  - id: bern_docs
    name: Bern Dokumente
    publisher: Stadt Bern
    authority: official_info
    level: municipal
    extent_id: CH-BE-351
    connector: html
    tier: 2
    languages: [de]
    config: {start_urls: ["https://www.example.ch/"], allow_prefixes: ["https://www.example.ch/"],
             pdf_allow_prefixes: ["https://www.bern.ch/docs/"]}
"""


def test_rejects_sources_with_overlapping_prefixes(tmp_path):
    """Two sources crawling the same URLs would fight over who owns each document."""
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST + OVERLAP)
    with pytest.raises(ValueError, match=r"bern_city.*bern_docs"):
        load_manifest(path)


def test_accepts_sources_with_disjoint_prefixes(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST + OVERLAP.replace("https://www.bern.ch/docs/", "https://www.stadt-bern.ch/"))
    assert len(load_manifest(path).sources) == 3
