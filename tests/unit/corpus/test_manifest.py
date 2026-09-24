import re

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


SITE_CONFIG = ('config: {start_urls: ["https://www.bern.ch/"], allow_prefixes: ["https://www.bern.ch/"], '
               'language_links_selector: "nav#language a[href]", content_selector: "#content", '
               'pdf_link_patterns: ["^https://www\\\\.bern\\\\.ch/p/"], sitemap_urls: ["https://www.bern.ch/sitemap.xml.gz"], '
               'sitemap_include: ["/themen/"], deny_patterns: ["/archiv/"]}')
BERN_CONFIG = 'config: {start_urls: ["https://www.bern.ch/"], allow_prefixes: ["https://www.bern.ch/"]}'


def test_accepts_site_adaptation_keys(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST.replace(BERN_CONFIG, SITE_CONFIG))
    [spec] = select_sources(load_manifest(path), tier=2, source_ids=("bern_city",))
    assert spec.config["sitemap_include"] == ["/themen/"]


def test_accepts_delay_seconds(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST.replace(BERN_CONFIG, BERN_CONFIG.replace("}", ", delay_seconds: 3}")))
    [spec] = select_sources(load_manifest(path), tier=2, source_ids=("bern_city",))
    assert spec.config["delay_seconds"] == 3


@pytest.mark.parametrize("bad_value", ["-1", "true", '"3"'])
def test_rejects_invalid_delay_seconds(tmp_path, bad_value):
    path = tmp_path / "m.yaml"
    config = BERN_CONFIG.replace("}", f", delay_seconds: {bad_value}}}")
    path.write_text(MANIFEST.replace(BERN_CONFIG, config))
    with pytest.raises(ValueError, match="delay_seconds"):
        load_manifest(path)


@pytest.mark.parametrize(("old", "new", "message"), [
    ('"^https://www\\\\.bern\\\\.ch/p/"', '"(unclosed"', "pdf_link_patterns"),
    ('["/themen/"]', '["[a-"]', "sitemap_include"),
    ('"nav#language a[href]"', '"nav#language a[href"', "language_links_selector"),
    ('"#content"', '"##"', "content_selector"),
    ('["https://www.bern.ch/sitemap.xml.gz"]', '["/sitemap.xml"]', "sitemap_urls"),
    ('["/themen/"]', '"/themen/"', "sitemap_include"),
    ('["/archiv/"]', '["(archiv"]', "deny_patterns"),
])
def test_rejects_invalid_site_adaptation_keys(tmp_path, old, new, message):
    path = tmp_path / "m.yaml"
    config = SITE_CONFIG.replace(old, new)
    assert config != SITE_CONFIG
    path.write_text(MANIFEST.replace(BERN_CONFIG, config))
    with pytest.raises(ValueError, match=message):
        load_manifest(path)


JSON_SOURCE = """
  - id: sz_holidays
    name: Schulferien Schwyz
    publisher: Kanton Schwyz
    authority: official_info
    level: cantonal
    extent_id: CH-SZ
    connector: json
    tier: 2
    languages: [de]
    config:
      url: "https://data.sz.ch/records?limit={size}&offset={offset}"
      paging: {style: offset, size: 100}
      records_path: results
      id_template: "{schuljahr}-{name_schule}"
      title_template: "Schulferien {schuljahr}: {name_schule}"
      text_template: "Herbstferien {herbstferien_start} bis {herbstferien_ende}"
"""


def _json_manifest(tmp_path, old=None, new=None):
    source = JSON_SOURCE if old is None else JSON_SOURCE.replace(old, new)
    assert old is None or source != JSON_SOURCE
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST + source)
    return path


def test_accepts_a_json_source(tmp_path):
    [spec] = select_sources(load_manifest(_json_manifest(tmp_path)), tier=2, source_ids=("sz_holidays",))
    assert spec.connector == "json"
    assert spec.config["paging"] == {"style": "offset", "size": 100}


@pytest.mark.parametrize(("old", "new", "message"), [
    ('url: "https://data.sz.ch/records?limit={size}&offset={offset}"', 'url: "/records"', "config.url"),
    ("offset={offset}", "offset={start}", "may only use"),
    ("{style: offset, size: 100}", "{style: scroll}", "paging.style"),
    ("limit={size}&offset={offset}", "limit={size}", "needs {offset} in config.url"),
    ("{style: offset, size: 100}", "{style: offset, size: 0}", "size must be"),
    ("      records_path: results\n", "", "records_path"),
    ('"{schuljahr}-{name_schule}"', '"{schuljahr"', "id_template"),
    ('      text_template: "Herbstferien {herbstferien_start} bis {herbstferien_ende}"\n', "",
     "text_template or config.html_path"),
])
def test_rejects_invalid_json_config(tmp_path, old, new, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        load_manifest(_json_manifest(tmp_path, old, new))


def test_rejects_an_empty_robots_exception_reason(tmp_path):
    line = '      text_template: "Herbstferien {herbstferien_start} bis {herbstferien_ende}"\n'
    with pytest.raises(ValueError, match="robots_exception_reason"):
        load_manifest(_json_manifest(tmp_path, line, line + '      robots_exception_reason: " "\n'))
