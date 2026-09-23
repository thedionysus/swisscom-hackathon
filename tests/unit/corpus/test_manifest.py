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
