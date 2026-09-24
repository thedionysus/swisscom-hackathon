"""`enrich` translates a document and places it at an extent. It no longer decides its topics.

That judgement moved to the chunk, and `ingest/context.py` makes it; the tests that
covered `_merge_tags` and the per-document classifier now live in `test_context.py`.
"""

from swiss_grounding.ingest.enrich import enrich
from swiss_grounding.ingest.llm import FakeLLM
from swiss_grounding.ingest.models import FetchedDocument, Section
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree
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


def fetched(language="de", text="Hunde in der Stadt Zürich müssen an die Leine."):
    return FetchedDocument(source_id="zh_ch", url="https://www.zh.ch/x", title="Hunde", language=language,
                           sections=(Section("Hunde", None, text),))


def test_translates_non_english_title_and_sections_and_narrows():
    llm = RecordingLLM()
    out = enrich(fetched(), source(), TREE, llm)
    assert out.title_en == "[de->en] Hunde"
    assert out.sections_en[0].text.startswith("[de->en]")
    assert out.sections_en[0].heading_path == "Hunde"
    assert out.extent_id == "CH-ZH-261"
    assert len(llm.translated) == 2


def test_english_is_not_translated():
    llm = RecordingLLM()
    out = enrich(fetched(language="en", text="Dogs in Zurich."), source(), TREE, llm)
    assert llm.translated == [] and out.title_en == "Hunde"


def test_law_sources_never_narrow():
    out = enrich(fetched(language="en", text="Applies in Zurich only."),
                 source(authority="cantonal_law", allow_narrowing=False), TREE, FakeLLM())
    assert out.extent_id == "CH-ZH" and out.extent_reason == "source_default"


class RaisingLLM(FakeLLM):
    def summarise(self, title_en, text_en):
        raise AssertionError("enrich must not summarise: that call belongs to the chunk step")

    def describe(self, summary_en, heading_path, text_en, text_original, categories):
        raise AssertionError("enrich must not describe: that call belongs to the chunk step")


def test_enrichment_asks_the_model_for_nothing_but_translation():
    """The per-document classify call is gone, not moved: every topic judgement is now per chunk,
    and paying for a document-level one as well would be a call per document of pure waste."""
    out = enrich(fetched(language="en", text="Waste collection for dogs."), source(), TREE, RaisingLLM())
    assert out.title_en == "Hunde"


def test_a_blank_section_is_not_sent_to_the_model():
    """Nothing to translate, so nothing is asked: the model's reply is validated as non-empty, and
    an empty section is the one case where empty is not a failure."""
    llm = RecordingLLM()
    doc = FetchedDocument(source_id="zh_ch", url="https://www.zh.ch/x", title="Hunde", language="de",
                          sections=(Section("Hunde", None, "  "), Section("Katzen", None, "Miau.")))
    out = enrich(doc, source(), TREE, llm)
    assert [t for t, _ in llm.translated] == ["Miau.", "Hunde"]
    assert out.sections_en[0].text == "  " and out.sections_en[1].text == "[de->en] Miau."
