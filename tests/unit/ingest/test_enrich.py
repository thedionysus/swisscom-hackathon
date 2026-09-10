from swiss_grounding.ingest.enrich import enrich
from swiss_grounding.ingest.llm import FakeLLM
from swiss_grounding.ingest.models import FetchedDocument, Section
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.categories import CATEGORIES
from swiss_grounding.registry.models import Source

TREE = LocationTree.from_locations(seed_locations())


class RecordingLLM(FakeLLM):
    def __init__(self):
        self.translated = []

    def translate(self, text, source_language):
        self.translated.append((text, source_language))
        return f"[{source_language}->en] {text}"


def source(**o):
    base = {"id": "zh_ch", "name": "ZH", "base_url": "https://www.zh.ch", "default_extent_id": "CH-ZH",
            "authority": "official_info", "categories": ("dogs",), "fetch_strategy": "html_crawl",
            "allow_narrowing": True}
    return Source(**{**base, **o})


def fetched(language="de", text="Hunde in Wiedikon, Zürich, müssen an die Leine."):
    return FetchedDocument(source_id="zh_ch", url="https://www.zh.ch/x", title="Hunde", language=language,
                           sections=(Section("Hunde", None, text),))


def test_translates_non_english_title_and_sections_and_narrows():
    llm = RecordingLLM()
    out = enrich(fetched(), source(), TREE, llm, CATEGORIES)
    assert out.title_en == "[de->en] Hunde"
    assert out.sections_en[0].text.startswith("[de->en]")
    assert out.sections_en[0].heading_path == "Hunde"
    assert out.extent_id == "CH-ZH-261"
    assert len(llm.translated) == 2


def test_english_is_not_translated():
    llm = RecordingLLM()
    out = enrich(fetched(language="en", text="Dogs in Zurich."), source(), TREE, llm, CATEGORIES)
    assert llm.translated == [] and out.title_en == "Hunde"


def test_source_default_categories_are_kept_and_merged_with_llm_tags():
    out = enrich(fetched(language="en", text="Waste collection for dogs."), source(categories=("dogs",)), TREE, FakeLLM(), CATEGORIES)
    ids = {t.id: t.confidence for t in out.categories}
    assert ids["dogs"] == 1.0            # source default wins at full confidence
    assert "waste" in ids


def test_law_sources_never_narrow():
    out = enrich(fetched(language="en", text="Applies in Zurich only."), source(authority="cantonal_law", allow_narrowing=False), TREE, FakeLLM(), CATEGORIES)
    assert out.extent_id == "CH-ZH" and out.extent_reason == "source_default"


def test_categories_are_sorted_by_confidence_then_id():
    out = enrich(fetched(language="en", text="Hiking with dogs and waste bins."), source(categories=()), TREE, FakeLLM(), CATEGORIES)
    confidences = [t.confidence for t in out.categories]
    assert confidences == sorted(confidences, reverse=True)
    ids = [t.id for t in out.categories]
    assert ids == sorted(ids)      # all fake tags share the same confidence, so ids are alphabetical
