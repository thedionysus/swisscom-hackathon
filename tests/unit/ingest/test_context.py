"""Per-chunk context and topics (ADR 0005, ADR 0003).

Every assertion about cost here is load-bearing: one model call per chunk is paid on every
future ingest and on the backfill, so the tests count calls as well as check output.
"""

import pytest

from swiss_grounding.ingest.context import (
    SOURCE_FALLBACK_CONFIDENCE,
    describe_chunks,
    document_topics,
    indexed_text,
    merge_topics,
)
from swiss_grounding.ingest.llm import FAKE_KEYWORD_CONFIDENCE, FakeLLM
from swiss_grounding.ingest.models import CategoryTag, ChunkContext, ChunkDraft
from swiss_grounding.registry.categories import CATEGORIES
from swiss_grounding.registry.models import Source

WASTE = CategoryTag("waste", 0.9)


def source(**overrides) -> Source:
    base = {"id": "zh_ch", "name": "Canton of Zurich", "base_url": "https://www.zh.ch",
            "default_extent_id": "CH-ZH", "authority": "official_info", "categories": ("dogs",),
            "fetch_strategy": "html_crawl"}
    return Source(**{**base, **overrides})


def draft(heading="Art. 28", text_en="Anyone who intentionally", text_original="Wer vorsätzlich", ordinal=0):
    return ChunkDraft(ordinal=ordinal, heading_path=heading, anchor=None,
                      text_original=text_original, text_en=text_en)


class CountingLLM(FakeLLM):
    """Records what was asked, so a test can assert the number of calls as well as the output."""

    def __init__(self, verdict=None):
        self.summarised: list[tuple[str, str]] = []
        self.described: list[dict] = []
        self._verdict = verdict or {}

    def summarise(self, title_en, text_en):
        self.summarised.append((title_en, text_en))
        return f"a summary of {title_en}"

    def describe(self, summary_en, heading_path, text_en, text_original, categories):
        self.described.append({"summary": summary_en, "heading": heading_path, "text_en": text_en,
                               "text_original": text_original})
        return ChunkContext(
            context_en=f"From {summary_en}. Covers {heading_path}. {text_original}",
            topics=(WASTE,),
            boilerplate=self._verdict.get(heading_path, False),
        )


class SilentLLM(FakeLLM):
    """Describes every chunk but names no category for any of it."""

    def summarise(self, title_en, text_en):
        return "a summary"

    def describe(self, summary_en, heading_path, text_en, text_original, categories):
        return ChunkContext(context_en="Some context.", topics=(), boilerplate=False)


class ForbiddenLLM(FakeLLM):
    def summarise(self, title_en, text_en):
        raise AssertionError("summarise must not be called")

    def describe(self, summary_en, heading_path, text_en, text_original, categories):
        raise AssertionError("describe must not be called")


def describe(chunks, llm, src=None, title_en="Animal Welfare Act", document_text_en="Zweck."):
    return describe_chunks(chunks, source=src or source(), title_en=title_en,
                           document_text_en=document_text_en, llm=llm, categories=CATEGORIES)


# --- what the index sees --------------------------------------------------------------------


def test_context_is_indexed_but_never_cited():
    """The indexing half, named as the plan names it. The citation half of the same property is
    `tests/integration/test_context_never_cited.py`, which needs a database and a real search."""
    joined = indexed_text("From the Animal Welfare Act. Sets penalties", "Anyone who intentionally")
    assert "Animal Welfare Act" in joined      # the embedding and the tsv see it
    assert joined == "From the Animal Welfare Act. Sets penalties Anyone who intentionally"


def test_an_empty_context_indexes_the_text_exactly_as_before():
    """`context_en` defaults to empty, so the join must not prepend a separator to nothing."""
    assert indexed_text("", "Anyone who intentionally") == "Anyone who intentionally"


def test_the_boundary_words_do_not_fuse():
    assert "penaltiesAnyone" not in indexed_text("Sets penalties", "Anyone who")


# --- one call per chunk, one summary per document -------------------------------------------


def test_one_summary_call_per_document_and_one_describe_call_per_chunk():
    llm = CountingLLM()
    out = describe((draft(heading="Art. 1", ordinal=0), draft(heading="Art. 2", ordinal=1)), llm)
    assert len(llm.summarised) == 1
    assert [d["heading"] for d in llm.described] == ["Art. 1", "Art. 2"]
    assert len(out) == 2


def test_every_chunk_of_a_document_shares_one_summary():
    """The summary is what makes a per-chunk call affordable: it is generated once and repeated."""
    llm = CountingLLM()
    describe((draft(heading="Art. 1"), draft(heading="Art. 2"), draft(heading="Art. 3")), llm)
    assert {d["summary"] for d in llm.described} == {"a summary of Animal Welfare Act"}


def test_the_generated_context_reaches_the_chunk():
    out = describe((draft(),), CountingLLM())
    assert out[0].context_en.startswith("From a summary of Animal Welfare Act")


def test_the_chunk_text_is_left_untouched():
    """Context is added beside the text, never folded into it: the citation quotes the text."""
    out = describe((draft(text_en="Anyone who intentionally"),), CountingLLM())
    assert out[0].text_en == "Anyone who intentionally"
    assert out[0].text_original == "Wer vorsätzlich"


# --- the original wording stays reachable ----------------------------------------------------


def test_the_original_wording_is_offered_to_the_model():
    """A German compound with no English cognate can only survive if the model is shown it."""
    llm = CountingLLM()
    describe((draft(text_en="Collection of green waste", text_original="Grüngutabfuhr"),), llm)
    assert llm.described[0]["text_original"] == "Grüngutabfuhr"


def test_context_keeps_the_original_term():
    """FakeLLM stands in for the real model's instruction to keep an untranslatable term."""
    out = describe((draft(text_en="Collection of green waste", text_original="Grüngutabfuhr"),), FakeLLM())
    assert "Grüngutabfuhr" in out[0].context_en


# --- boilerplate ------------------------------------------------------------------------------


def test_a_heading_known_to_be_furniture_is_dropped_without_paying_for_a_verdict():
    llm = CountingLLM()
    out = describe((draft(heading="Navigation"), draft(heading="Art. 28")), llm)
    assert [c.heading_path for c in out] == ["Art. 28"]
    assert [d["heading"] for d in llm.described] == ["Art. 28"]


def test_a_document_that_is_entirely_furniture_costs_nothing_at_all():
    """The 79 canton and city chunks are all `Navigation`; not one of them earns a summary call."""
    out = describe((draft(heading="Navigation"), draft(heading="Error Page (404)")), ForbiddenLLM())
    assert out == ()


def test_the_model_verdict_drops_a_chunk_the_heading_rules_never_see():
    llm = CountingLLM(verdict={"Opening hours": True})
    out = describe((draft(heading="Opening hours"), draft(heading="Art. 28")), llm)
    assert [c.heading_path for c in out] == ["Art. 28"]


def test_a_dropped_chunk_leaves_the_others_ordinals_alone():
    """An ordinal is only an ordering key; a gap records honestly that a chunk was dropped."""
    llm = CountingLLM(verdict={"Opening hours": True})
    out = describe((draft(heading="Art. 1", ordinal=0), draft(heading="Opening hours", ordinal=1),
                    draft(heading="Art. 3", ordinal=2)), llm)
    assert [c.ordinal for c in out] == [0, 2]


# --- topics are per chunk (ADR 0003) ----------------------------------------------------------


def test_the_models_per_chunk_topics_win_over_the_sources_declared_ones():
    out = describe((draft(),), CountingLLM(), src=source(categories=("dogs",)))
    assert out[0].topics == (WASTE,)


def test_a_single_declared_category_applies_when_the_model_names_none():
    tags = merge_topics(source(categories=("waste",)), model_topics=())
    assert {t.id for t in tags} == {"waste"}
    assert tags[0].confidence == SOURCE_FALLBACK_CONFIDENCE
    assert tags[0].confidence < 1.0        # a fallback is not a certainty


def test_several_declared_categories_never_become_one_chunks_topics():
    """The defect this plan exists to fix, re-entered through the fallback door: `fedlex` declares
    five, and a definitions article that the model tags with nothing is not about all five."""
    assert merge_topics(source(categories=("dogs", "hiking", "safety", "transport", "waste")),
                        model_topics=()) == ()


def test_a_templated_source_still_falls_back_to_everything_it_declares():
    """There is no model judgement to defer to, so the declaration is the whole judgement."""
    tags = merge_topics(source(categories=("waste", "transport"), llm_tagging=False), model_topics=())
    assert {t.id for t in tags} == {"waste", "transport"}


def test_the_fallback_is_not_reached_when_the_model_named_something():
    tags = merge_topics(source(categories=("dogs", "waste")), model_topics=(WASTE,))
    assert tags == (WASTE,)


def test_a_chunk_of_a_multi_category_source_can_end_with_no_topics_at_all():
    """Accepted deliberately: under Task 8's hard filter such a chunk is unreachable, and that is
    better than reaching it under five topics that are false of it."""
    out = describe((draft(text_en="Definitions apply throughout."),), SilentLLM(),
                   src=source(categories=("dogs", "hiking", "waste")))
    assert out[0].topics == ()


def test_open_erz_keeps_the_topic_its_whole_feed_is_about():
    """The waste calendar is one category by declaration; Task 8's filter makes an untagged
    calendar unreachable, which would lose every collection date in the index."""
    out = describe((draft(heading="Waste collection cardboard in 8003 on 2026-09-25",
                          text_en="Collection of cardboard."),), ForbiddenLLM(),
                   src=source(id="open_erz", name="Open ERZ", categories=("waste",), llm_tagging=False))
    assert out[0].topics == (CategoryTag("waste", SOURCE_FALLBACK_CONFIDENCE),)


def test_two_chunks_of_one_document_can_carry_different_topics():
    """The defect ADR 0003 names: one tag set copied onto every chunk of a hundred-article act."""
    out = describe((draft(heading="Leinenpflicht", text_en="Dogs must be kept on a leash.", ordinal=0),
                    draft(heading="Karton", text_en="Cardboard collection is on Tuesday.", ordinal=1)),
                   FakeLLM(), src=source(categories=()))
    first, second = ({t.id for t in c.topics} for c in out)
    assert first != second
    assert "dogs" in first and "waste" in second


def test_a_document_rolls_its_chunks_topics_up_at_their_own_confidence():
    chunks = (
        ChunkDraft(0, "A", None, "o", "e", topics=(CategoryTag("dogs", 0.4),)),
        ChunkDraft(1, "B", None, "o", "e", topics=(CategoryTag("dogs", 0.9), CategoryTag("waste", 0.2))),
    )
    assert document_topics(chunks) == (CategoryTag("dogs", 0.9), CategoryTag("waste", 0.2))


def test_a_document_with_no_chunks_asserts_no_topics():
    assert document_topics(()) == ()


# --- templated sources cost nothing (Step 5) ---------------------------------------------------


def test_a_templated_source_is_described_from_its_own_template_with_no_model_call():
    """`open_erz` renders self-describing records; paying a model to restate them is waste."""
    out = describe(
        (draft(heading="Waste collection cardboard in 8003 on 2026-09-25",
               text_en="Collection of cardboard in Zurich postal code 8003 on 2026-09-25."),),
        ForbiddenLLM(),
        src=source(id="open_erz", name="Open ERZ waste calendar", categories=("waste",), llm_tagging=False),
        title_en="Waste collection cardboard in 8003 on 2026-09-25",
    )
    assert len(out) == 1
    assert "Open ERZ waste calendar" in out[0].context_en
    assert "Waste collection cardboard in 8003 on 2026-09-25" in out[0].context_en
    assert out[0].topics == (CategoryTag("waste", SOURCE_FALLBACK_CONFIDENCE),)


def test_a_templated_source_still_drops_page_furniture():
    out = describe((draft(heading="Navigation"),), ForbiddenLLM(),
                   src=source(llm_tagging=False))
    assert out == ()


# --- failures are not absorbed ------------------------------------------------------------------


class BrokenLLM(FakeLLM):
    def describe(self, summary_en, heading_path, text_en, text_original, categories):
        raise RuntimeError("model down")


def test_a_failed_description_is_not_swallowed():
    """A chunk silently dropped for a transport error would leave a hole nothing records."""
    with pytest.raises(RuntimeError, match="model down"):
        describe((draft(),), BrokenLLM())


def test_the_fake_tags_each_chunk_at_its_own_confidence():
    out = describe((draft(text_en="Cardboard collection and waste disposal."),), FakeLLM(),
                   src=source(categories=()))
    assert all(t.confidence == FAKE_KEYWORD_CONFIDENCE for t in out[0].topics)


def test_topics_are_sorted_by_confidence_then_id():
    """A stable order, so a stored tag list is comparable between runs."""
    topics = merge_topics(source(categories=()), model_topics=(
        CategoryTag("waste", 0.4), CategoryTag("dogs", 0.9), CategoryTag("hiking", 0.9)))
    assert [t.id for t in topics] == ["dogs", "hiking", "waste"]


def test_the_source_fallback_is_sorted_the_same_way():
    ids = [t.id for t in merge_topics(source(categories=("waste", "dogs"), llm_tagging=False), ())]
    assert ids == ["dogs", "waste"]
