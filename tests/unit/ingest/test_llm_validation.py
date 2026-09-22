"""Model output is a boundary: what comes back is validated before anything downstream sees it."""

import json

import pytest

from swiss_grounding.ingest.errors import EnrichmentError
from swiss_grounding.ingest.llm import AnthropicLLM, parse_description
from swiss_grounding.ingest.models import CategoryTag
from swiss_grounding.registry.categories import CATEGORIES

KNOWN = ("dogs", "waste")


class Message:
    def __init__(self, content):
        self.content = content


class FakeMessages:
    def __init__(self, blocks):
        self._blocks = blocks
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return Message(self._blocks)


class Block:
    def __init__(self, text):
        self.text = text


class BlockWithoutText:
    """A content block the SDK may return that carries no text at all (a tool use, say)."""


class FakeClient:
    def __init__(self, returns=None, blocks=None):
        self.messages = FakeMessages([Block(returns)] if blocks is None else blocks)


def anthropic(returns=None, blocks=None):
    return AnthropicLLM(model="m", client=FakeClient(returns=returns, blocks=blocks))


def test_empty_translation_is_an_error_not_an_empty_string():
    llm = anthropic(returns="")
    with pytest.raises(EnrichmentError):
        llm.translate("Tierschutzgesetz", "de")


def test_whitespace_only_translation_is_an_error():
    llm = anthropic(returns="   \n  ")
    with pytest.raises(EnrichmentError):
        llm.translate("Tierschutzgesetz", "de")


def test_a_reply_made_only_of_blocks_without_text_is_an_error():
    llm = anthropic(blocks=[BlockWithoutText()])
    with pytest.raises(EnrichmentError):
        llm.translate("Tierschutzgesetz", "de")


def test_a_non_empty_translation_is_returned_stripped():
    assert anthropic(returns="  Animal Welfare Act \n").translate("Tierschutzgesetz", "de") == "Animal Welfare Act"


def tagged(categories):
    """A well-formed description carrying `categories`, so the tag rules can be exercised alone."""
    return json.dumps({"context": "About dogs.", "boilerplate": False, "categories": categories})


def test_an_empty_category_list_parses_as_no_topics():
    assert parse_description(tagged([]), KNOWN).topics == ()


def test_an_empty_response_is_rejected():
    with pytest.raises(EnrichmentError):
        parse_description("", KNOWN)


def test_a_tag_without_a_confidence_is_rejected_not_read_as_zero():
    """A tag the model expressed no confidence in must not become a full-strength topic filter."""
    with pytest.raises(EnrichmentError, match="confidence"):
        parse_description(tagged([{"id": "dogs"}]), KNOWN)


def test_a_tag_with_a_non_numeric_confidence_is_rejected():
    with pytest.raises(EnrichmentError, match="confidence"):
        parse_description(tagged([{"id": "dogs", "confidence": "high"}]), KNOWN)


def test_an_unknown_id_is_discarded_before_its_confidence_is_judged():
    """A category we do not have cannot reach storage under any ordering, so its confidence is never
    read. Judging it first would fail a whole document over an item that was irrelevant anyway."""
    raw = tagged([{"id": "unicorns"}, {"id": "dogs", "confidence": 0.4}])
    assert parse_description(raw, KNOWN).topics == (CategoryTag("dogs", 0.4),)


def test_a_boolean_confidence_is_rejected():
    """`float(True)` is 1.0: a bool would become maximum confidence from a model that stated none."""
    with pytest.raises(EnrichmentError, match="confidence"):
        parse_description(tagged([{"id": "dogs", "confidence": True}]), KNOWN)


def test_a_well_formed_tag_still_parses():
    assert parse_description(tagged([{"id": "dogs", "confidence": 0.8}]), KNOWN).topics == (
        CategoryTag("dogs", 0.8),)


def test_a_category_list_that_is_not_a_list_is_rejected():
    with pytest.raises(EnrichmentError, match="not a list"):
        parse_description(tagged(5), KNOWN)


def test_a_tag_that_is_not_an_object_is_malformed_output():
    """`["dogs"]` is the model dropping the schema, not naming no category. Read as an empty
    answer it would hand the chunk its source's declared categories instead."""
    for items in (["dogs", "waste"], [["dogs"]], [None]):
        with pytest.raises(EnrichmentError, match="not an object"):
            parse_description(tagged(items), KNOWN)


def test_one_malformed_tag_among_well_formed_ones_is_not_dropped_quietly():
    """A partial silent drop is undetectable by a caller counting tags."""
    with pytest.raises(EnrichmentError, match="not an object"):
        parse_description(tagged([{"id": "dogs", "confidence": 0.5}, "waste"]), KNOWN)


def test_the_confidence_error_names_the_offending_tag_not_the_whole_response():
    """The bad tag may be the seventh item, past any truncation of the response."""
    raw = tagged([{"id": "waste", "confidence": 0.5}, {"id": "dogs", "confidence": "high"}])
    with pytest.raises(EnrichmentError) as caught:
        parse_description(raw, KNOWN)
    message = str(caught.value)
    assert "dogs" in message and "waste" not in message


def test_an_empty_translation_names_the_call_without_leaking_the_text():
    """The exception type already says a translation came back empty; the message says which call,
    and does not spill source text into the log to do it."""
    with pytest.raises(EnrichmentError) as caught:
        anthropic(returns="").translate("Tierschutzgesetz vom 16. Dezember 2005", "de")
    message = str(caught.value)
    assert "translat" in message and "de" in message
    assert "Tierschutzgesetz" not in message and "Translate the following" not in message


# --- describe(): context, topics and a boilerplate verdict in one call (ADR 0005) -------------


def described(raw):
    return anthropic(returns=raw).describe(
        summary_en="the Animal Welfare Act", heading_path="Art. 28",
        text_en="Anyone who intentionally", text_original="Wer vorsätzlich", categories=CATEGORIES,
    )


def a_description(**overrides):
    body = {"context": "From the Animal Welfare Act. Sets penalties.",
            "categories": [{"id": "dogs", "confidence": 0.8}], "boilerplate": False}
    return json.dumps({**body, **overrides})


def test_a_well_formed_description_parses():
    out = described(a_description())
    assert out.context_en == "From the Animal Welfare Act. Sets penalties."
    assert out.topics == (CategoryTag("dogs", 0.8),)
    assert out.boilerplate is False


def test_an_empty_description_response_is_an_error():
    with pytest.raises(EnrichmentError):
        described("")


def test_an_unparseable_description_is_an_error():
    with pytest.raises(EnrichmentError, match="description"):
        described("I am afraid I cannot help with that.")


def test_a_description_tolerates_code_fences():
    assert described(f"```json\n{a_description()}\n```").topics == (CategoryTag("dogs", 0.8),)


def test_a_description_with_no_context_is_an_error():
    """The context is the whole point of the call; without it the chunk would index as before."""
    raw = json.dumps({"categories": [], "boilerplate": False})
    with pytest.raises(EnrichmentError, match="context"):
        described(raw)


def test_a_blank_context_on_a_kept_chunk_is_an_error():
    with pytest.raises(EnrichmentError, match="context"):
        described(a_description(context="   "))


def test_a_context_that_is_not_text_is_an_error():
    with pytest.raises(EnrichmentError, match="context"):
        described(a_description(context={"text": "..."}))


def test_a_blank_context_is_accepted_for_a_chunk_being_discarded():
    """A boilerplate chunk is dropped, so failing the whole document over its unused context
    would lose the articles around it to a judgement that was about to throw the chunk away."""
    out = described(a_description(context="", boilerplate=True))
    assert out.boilerplate is True


def test_a_discarded_chunk_is_validated_only_for_the_verdict_that_discards_it():
    """A missing key and an empty one must behave alike: the exemption exists to stop a chunk on
    its way to the bin failing the whole document, and it fails at that if the shape decides."""
    for raw in (json.dumps({"boilerplate": True}),
                json.dumps({"boilerplate": True, "context": ""}),
                json.dumps({"boilerplate": True, "context": "Navigation menu."})):
        assert described(raw).boilerplate is True


def test_a_kept_chunk_with_no_context_key_is_an_error():
    with pytest.raises(EnrichmentError, match="context"):
        described(json.dumps({"boilerplate": False, "categories": []}))


def test_a_missing_categories_key_is_not_an_answer_of_none():
    """`{"categories": []}` is the model saying none apply. Omitting the key is the model ignoring
    the schema, and reading it as "none named" is what decides whether the source fallback fires."""
    with pytest.raises(EnrichmentError, match="categories"):
        described(json.dumps({"context": "About dogs.", "boilerplate": False}))


def test_an_empty_categories_list_is_still_an_answer():
    assert described(a_description(categories=[])).topics == ()


def test_a_missing_boilerplate_verdict_is_an_error():
    """Read as false, an absent verdict would index page furniture as evidence."""
    raw = json.dumps({"context": "Navigation menu.", "categories": []})
    with pytest.raises(EnrichmentError, match="boilerplate"):
        described(raw)


@pytest.mark.parametrize("verdict", ["true", "yes", 1, 0, None, [], "false"])
def test_only_a_real_boolean_is_a_boilerplate_verdict(verdict):
    """`bool("false")` is True and `bool(0)` is False: a truthiness test here reads the model
    backwards. This is the mirror of `_confidence` rejecting a bool, and must not reuse it."""
    with pytest.raises(EnrichmentError, match="boilerplate"):
        described(a_description(boilerplate=verdict))


def test_description_topics_obey_the_same_rules_as_tags():
    with pytest.raises(EnrichmentError, match="confidence"):
        described(a_description(categories=[{"id": "dogs"}]))
    with pytest.raises(EnrichmentError, match="not an object"):
        described(a_description(categories=["dogs"]))
    assert described(a_description(categories=[{"id": "unicorns", "confidence": 0.9}])).topics == ()


def test_naming_no_category_is_an_answer_not_an_error():
    assert described(a_description(categories=[])).topics == ()


def test_context_keeps_the_original_term():
    """A term with no English cognate can only be kept if the model is shown the original."""
    llm = anthropic(returns=a_description())
    llm.describe(summary_en="the waste calendar", heading_path="Grüngut",
                 text_en="Collection of green waste", text_original="Grüngutabfuhr",
                 categories=CATEGORIES)
    prompt = llm._client.messages.calls[0]["messages"][0]["content"]
    assert "Grüngutabfuhr" in prompt and "the waste calendar" in prompt


def test_a_failed_description_names_the_chunk_without_leaking_its_text():
    with pytest.raises(EnrichmentError) as caught:
        described("")
    message = str(caught.value)
    assert "Art. 28" in message
    assert "Wer vorsätzlich" not in message and "Anyone who intentionally" not in message


def test_an_empty_summary_is_an_error_not_a_blank_document_subject():
    """Every chunk of the document repeats the summary; an empty one would say nothing, N times."""
    with pytest.raises(EnrichmentError) as caught:
        anthropic(returns="").summarise("Tierschutzgesetz", "Zweck dieses Gesetzes ist es")
    assert "Tierschutzgesetz" in str(caught.value)
    assert "Zweck dieses Gesetzes" not in str(caught.value)


def test_a_summary_is_returned_stripped():
    assert anthropic(returns="  The Animal Welfare Act.  ").summarise("x", "y") == "The Animal Welfare Act."
