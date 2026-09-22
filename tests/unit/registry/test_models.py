import pytest

from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.models import Source, extent_level_from_id


def _source(**overrides):
    base = {"id": "zh_ch", "name": "ZH", "base_url": "https://www.zh.ch", "default_extent_id": "CH-ZH",
            "authority": "official_info", "fetch_strategy": "html_crawl"}
    return Source(**{**base, **overrides})


def test_llm_tagging_defaults_to_true():
    assert _source().llm_tagging is True


def test_llm_tagging_can_be_disabled():
    assert _source(llm_tagging=False).llm_tagging is False


# --- ADR 0007: authority follows the publisher ---------------------------------------------------

def test_extent_level_is_read_from_the_id():
    assert extent_level_from_id("CH").value == "country"
    assert extent_level_from_id("CH-ZH").value == "canton"
    assert extent_level_from_id("CH-ZH-261").value == "municipality"
    assert extent_level_from_id("CH-ZH-261-K3").value == "neighborhood"


def test_federal_law_only_from_fedlex_at_country_level():
    _source(authority="federal_law", fetch_strategy="fedlex_sparql", default_extent_id="CH",
            base_url="https://www.fedlex.admin.ch")
    with pytest.raises(ValueError, match="registered official law platform"):
        _source(authority="federal_law", fetch_strategy="html_crawl", default_extent_id="CH",
                base_url="https://www.ch.ch")
    with pytest.raises(ValueError, match="country level"):
        _source(authority="federal_law", fetch_strategy="fedlex_sparql", default_extent_id="CH-ZH",
                base_url="https://www.fedlex.admin.ch")


def test_cantonal_law_only_from_the_cantons_own_collection():
    ok = _source(authority="cantonal_law", fetch_strategy="html_crawl", default_extent_id="CH-ZH",
                 base_url="https://www.zh.ch", allow_narrowing=False)
    assert ok.authority == "cantonal_law"
    _source(authority="cantonal_law", fetch_strategy="api", default_extent_id="CH-BS",
            base_url="https://www.gesetzessammlung.bs.ch", allow_narrowing=False)
    with pytest.raises(ValueError, match="publishes the law of CH-ZH"):
        _source(authority="cantonal_law", fetch_strategy="html_crawl", default_extent_id="CH-BE",
                base_url="https://www.zh.ch", allow_narrowing=False)
    with pytest.raises(ValueError, match="registered official law platform"):
        _source(authority="cantonal_law", fetch_strategy="api", default_extent_id="CH-ZH",
                base_url="https://mcp.opencaselaw.ch", allow_narrowing=False)


def test_municipal_law_only_from_the_communes_own_platform_at_commune_level():
    _source(authority="municipal_law", fetch_strategy="pdf", default_extent_id="CH-ZH-261",
            base_url="https://www.stadt-zuerich.ch", allow_narrowing=False)
    with pytest.raises(ValueError, match="municipality level"):
        _source(authority="municipal_law", fetch_strategy="pdf", default_extent_id="CH-ZH-261-K3",
                base_url="https://www.stadt-zuerich.ch", allow_narrowing=False)


def test_official_info_on_a_government_domain_needs_no_reason():
    assert _source(base_url="https://www.zh.ch").authority_reason is None
    assert _source(base_url="https://www.bafu.admin.ch", default_extent_id="CH").authority == "official_info"


def test_official_info_on_another_host_needs_a_reason():
    with pytest.raises(ValueError, match="authority_reason"):
        _source(base_url="https://openerz.metaodi.ch", default_extent_id="CH-ZH-261")
    ok = _source(base_url="https://openerz.metaodi.ch", default_extent_id="CH-ZH-261",
                 authority_reason="re-serves the city's open-data export")
    assert ok.authority == "official_info"


def test_institutional_has_no_publisher_constraint():
    assert _source(authority="institutional", base_url="https://www.example.org").authority == "institutional"


def test_every_seed_source_satisfies_the_rules():
    ids = {s.id for s in load_seed_sources()}
    assert {"fedlex", "open_erz", "ch_ch"} <= ids
