import json

import pytest

from swiss_grounding.ingest.errors import EnrichmentError
from swiss_grounding.ingest.llm import AnthropicLLM, FakeLLM, build_llm, parse_description
from swiss_grounding.ingest.models import CategoryTag
from swiss_grounding.registry.categories import CATEGORIES


def test_fake_translate_is_identity():
    llm = FakeLLM()
    assert llm.translate("Hello", "en") == "Hello"
    assert llm.translate("Hallo Welt", "de") == "Hallo Welt"


def describe_with(llm, heading="Dogs in parks", text_en="Leash rules for dogs on hiking trails.",
                  text_original="Leinenpflicht"):
    return llm.describe(summary_en="a page about dogs", heading_path=heading, text_en=text_en,
                        text_original=text_original, categories=CATEGORIES)


def test_fake_describe_is_keyword_based_and_deterministic():
    llm = FakeLLM()
    described = describe_with(llm)
    ids = {t.id for t in described.topics}
    assert {"dogs", "hiking"} <= ids
    assert all(0 < t.confidence <= 1 for t in described.topics)
    assert described == describe_with(llm)


def test_fake_describe_names_the_document_and_the_section():
    described = describe_with(FakeLLM())
    assert "a page about dogs" in described.context_en and "Dogs in parks" in described.context_en
    assert described.boilerplate is False


def test_fake_summarise_is_deterministic_and_names_the_title():
    llm = FakeLLM()
    assert llm.summarise("Animal Welfare Act", "Zweck.") == llm.summarise("Animal Welfare Act", "Zweck.")
    assert "Animal Welfare Act" in llm.summarise("Animal Welfare Act", "Zweck.")


def description(**overrides):
    body = {"context": "About dogs.", "categories": [], "boilerplate": False}
    return json.dumps({**body, **overrides})


def test_parse_description_filters_unknown_ids_and_clamps_confidence():
    raw = description(categories=[{"id": "dogs", "confidence": 1.7},
                                  {"id": "unicorns", "confidence": 0.9},
                                  {"id": "waste", "confidence": -1}])
    assert parse_description(raw, ("dogs", "waste")).topics == (CategoryTag("dogs", 1.0),
                                                                CategoryTag("waste", 0.0))


def test_parse_description_bad_json_raises():
    with pytest.raises(EnrichmentError, match="unparseable response"):
        parse_description("not json", ("dogs",))


def test_parse_description_tolerates_code_fences():
    raw = "```json\n" + description(categories=[{"id": "dogs", "confidence": 0.5}]) + "\n```"
    assert parse_description(raw, ("dogs",)).topics == (CategoryTag("dogs", 0.5),)


def test_build_llm_fake_and_anthropic():
    assert isinstance(build_llm("fake", model="m", api_key=None), FakeLLM)
    assert isinstance(build_llm("anthropic", model="m", api_key="k"), AnthropicLLM)
    with pytest.raises(ValueError):
        build_llm("nope", model="m", api_key=None)
    with pytest.raises(ValueError, match="api key"):
        build_llm("anthropic", model="m", api_key=None)


def test_anthropic_backend_uses_client_and_extracts_text():
    class FakeMessages:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            prompt = kwargs["messages"][0]["content"]

            class Block:
                text = ('{"context":"About dogs.","categories":[{"id":"dogs","confidence":0.8}],'
                        '"boilerplate":false}') if "Categories:" in prompt else "Translated"

            class Msg:
                content = [Block()]  # noqa: RUF012

            return Msg()

    class FakeClient:
        def __init__(self):
            self.messages = FakeMessages()

    client = FakeClient()
    llm = AnthropicLLM(model="claude-sonnet-5", client=client)
    assert llm.translate("Hallo", "de") == "Translated"
    described = describe_with(llm, heading="T", text_en="text")
    assert described.topics == (CategoryTag("dogs", 0.8),)
    assert described.context_en == "About dogs."
    assert client.messages.calls[0]["model"] == "claude-sonnet-5"
