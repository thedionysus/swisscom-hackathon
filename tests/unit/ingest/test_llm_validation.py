"""Model output is a boundary: what comes back is validated before anything downstream sees it."""

import json

import pytest

from swiss_grounding.ingest.errors import EnrichmentError
from swiss_grounding.ingest.llm import AnthropicLLM, parse_tags
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


def test_empty_classification_output_is_an_error():
    llm = anthropic(returns="")
    with pytest.raises(EnrichmentError):
        llm.classify("Tierschutzgesetz", "Zweck dieses Gesetzes", CATEGORIES)


def test_no_categories_apply_is_an_answer_not_an_error():
    """`{"categories": []}` is the model saying none apply; it must not be treated as a failure."""
    llm = anthropic(returns=json.dumps({"categories": []}))
    assert llm.classify("Tierschutzgesetz", "Zweck dieses Gesetzes", CATEGORIES) == ()


def test_unparseable_classification_output_is_an_error():
    llm = anthropic(returns="I am afraid I cannot help with that.")
    with pytest.raises(EnrichmentError):
        llm.classify("Tierschutzgesetz", "Zweck dieses Gesetzes", CATEGORIES)


def test_parse_tags_accepts_an_empty_category_list():
    assert parse_tags(json.dumps({"categories": []}), KNOWN) == ()


def test_parse_tags_rejects_an_empty_response():
    with pytest.raises(EnrichmentError):
        parse_tags("", KNOWN)


def test_a_tag_without_a_confidence_is_rejected_not_read_as_zero():
    """A tag the model expressed no confidence in must not become a full-strength topic filter."""
    raw = json.dumps({"categories": [{"id": "dogs"}]})
    with pytest.raises(EnrichmentError, match="confidence"):
        parse_tags(raw, KNOWN)


def test_a_tag_with_a_non_numeric_confidence_is_rejected():
    raw = json.dumps({"categories": [{"id": "dogs", "confidence": "high"}]})
    with pytest.raises(EnrichmentError, match="confidence"):
        parse_tags(raw, KNOWN)


def test_an_unknown_id_is_discarded_before_its_confidence_is_judged():
    """A category we do not have cannot reach storage under any ordering, so its confidence is never
    read. Judging it first would fail a whole document over an item that was irrelevant anyway."""
    raw = json.dumps({"categories": [{"id": "unicorns"}, {"id": "dogs", "confidence": 0.4}]})
    assert parse_tags(raw, KNOWN) == (CategoryTag("dogs", 0.4),)


def test_a_boolean_confidence_is_rejected():
    """`float(True)` is 1.0: a bool would become maximum confidence from a model that stated none."""
    raw = json.dumps({"categories": [{"id": "dogs", "confidence": True}]})
    with pytest.raises(EnrichmentError, match="confidence"):
        parse_tags(raw, KNOWN)


def test_a_well_formed_tag_still_parses():
    raw = json.dumps({"categories": [{"id": "dogs", "confidence": 0.8}]})
    assert parse_tags(raw, KNOWN) == (CategoryTag("dogs", 0.8),)


def test_parse_tags_rejects_a_category_list_that_is_not_a_list():
    with pytest.raises(EnrichmentError, match="tag response"):
        parse_tags(json.dumps({"categories": 5}), KNOWN)


def test_a_tag_that_is_not_an_object_is_malformed_output():
    """`{"categories": ["dogs"]}` is the model dropping the schema, not naming no category. Read as
    an empty answer it would hand the document its source's declared categories instead."""
    for raw in ('{"categories": ["dogs", "waste"]}', '{"categories": [["dogs"]]}', '{"categories": [null]}'):
        with pytest.raises(EnrichmentError, match="not an object"):
            parse_tags(raw, KNOWN)


def test_one_malformed_tag_among_well_formed_ones_is_not_dropped_quietly():
    """A partial silent drop is undetectable by a caller counting tags."""
    raw = json.dumps({"categories": [{"id": "dogs", "confidence": 0.5}, "waste"]})
    with pytest.raises(EnrichmentError, match="not an object"):
        parse_tags(raw, KNOWN)


def test_the_confidence_error_names_the_offending_tag_not_the_whole_response():
    """The bad tag may be the seventh item, past any truncation of the response."""
    raw = json.dumps({"categories": [{"id": "waste", "confidence": 0.5}, {"id": "dogs", "confidence": "high"}]})
    with pytest.raises(EnrichmentError) as caught:
        parse_tags(raw, KNOWN)
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


def test_an_empty_classification_names_the_document_it_was_about():
    with pytest.raises(EnrichmentError) as caught:
        anthropic(returns="").classify("Animal Welfare Act", "Zweck dieses Gesetzes ist es", CATEGORIES)
    message = str(caught.value)
    assert "classif" in message and "Animal Welfare Act" in message
    assert "Zweck dieses Gesetzes" not in message
