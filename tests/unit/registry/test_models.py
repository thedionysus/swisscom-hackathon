from swiss_grounding.registry.models import Source


def _source(**overrides):
    base = {"id": "zh_ch", "name": "ZH", "base_url": "https://www.zh.ch", "default_extent_id": "CH-ZH",
            "authority": "official_info", "fetch_strategy": "html_crawl"}
    return Source(**{**base, **overrides})


def test_llm_tagging_defaults_to_true():
    assert _source().llm_tagging is True


def test_llm_tagging_can_be_disabled():
    assert _source(llm_tagging=False).llm_tagging is False
