import pytest

from swiss_grounding.registry.categories import CATEGORY_IDS
from swiss_grounding.registry.loader import load_source_yaml, load_seed_sources
from swiss_grounding.registry.models import Authority, FetchStrategy

VALID = """
id: zh_ch
name: Kanton Zürich
base_url: https://www.zh.ch
default_extent_id: CH-ZH
authority: official_info
categories: [hiking, dogs]
fetch_strategy: html_crawl
fetch_config:
  path_allowlist: ["/de/umwelt-tiere", "/de/sicherheit"]
allow_narrowing: true
license: "zh.ch terms of use"
"""


def test_loads_valid_source():
    s = load_source_yaml(VALID)
    assert s.id == "zh_ch"
    assert s.authority == Authority.OFFICIAL_INFO
    assert s.fetch_strategy == FetchStrategy.HTML_CRAWL
    assert s.categories == ("hiking", "dogs")
    assert s.allow_narrowing is True
    assert s.fetch_config["path_allowlist"] == ["/de/umwelt-tiere", "/de/sicherheit"]


def test_rejects_unknown_category():
    with pytest.raises(ValueError, match="category"):
        load_source_yaml(VALID.replace("dogs", "unicorns"))


def test_rejects_unknown_authority():
    with pytest.raises(ValueError):
        load_source_yaml(VALID.replace("official_info", "supreme"))


def test_rejects_narrowing_on_law():
    text = VALID.replace("official_info", "cantonal_law")
    with pytest.raises(ValueError, match="allow_narrowing"):
        load_source_yaml(text)


def test_seed_sources_load_and_reference_valid_categories():
    sources = load_seed_sources()
    ids = {s.id for s in sources}
    assert {"fedlex", "zh_ch", "stadt_zuerich", "ch_ch", "schweizer_wanderwege"} <= ids
    for s in sources:
        assert set(s.categories) <= set(CATEGORY_IDS)
