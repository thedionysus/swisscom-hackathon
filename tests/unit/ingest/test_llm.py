import json

import pytest

from swiss_grounding.ingest.llm import AnthropicLLM, FakeLLM, build_llm, parse_tags
from swiss_grounding.ingest.models import CategoryTag
from swiss_grounding.registry.categories import CATEGORIES


def test_fake_translate_is_identity():
    llm = FakeLLM()
    assert llm.translate("Hello", "en") == "Hello"
    assert llm.translate("Hallo Welt", "de") == "Hallo Welt"


def test_fake_classify_is_keyword_based_and_deterministic():
    llm = FakeLLM()
    tags = llm.classify("Dogs in parks", "Leash rules for dogs on hiking trails.", CATEGORIES)
    ids = {t.id for t in tags}
    assert {"dogs", "hiking"} <= ids
    assert all(0 < t.confidence <= 1 for t in tags)
    assert tags == llm.classify("Dogs in parks", "Leash rules for dogs on hiking trails.", CATEGORIES)


def test_parse_tags_filters_unknown_and_clamps():
    raw = json.dumps({"categories": [{"id": "dogs", "confidence": 1.7}, {"id": "unicorns", "confidence": 0.9}, {"id": "waste", "confidence": -1}]})
    assert parse_tags(raw, ("dogs", "waste")) == (CategoryTag("dogs", 1.0), CategoryTag("waste", 0.0))


def test_parse_tags_bad_json_raises():
    with pytest.raises(ValueError, match="tag response"):
        parse_tags("not json", ("dogs",))


def test_parse_tags_tolerates_code_fences():
    raw = "```json\n{\"categories\": [{\"id\": \"dogs\", \"confidence\": 0.5}]}\n```"
    assert parse_tags(raw, ("dogs",)) == (CategoryTag("dogs", 0.5),)


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
                text = '{"categories":[{"id":"dogs","confidence":0.8}]}' if "Categories:" in prompt else "Translated"

            class Msg:
                content = [Block()]  # noqa: RUF012

            return Msg()

    class FakeClient:
        def __init__(self):
            self.messages = FakeMessages()

    client = FakeClient()
    llm = AnthropicLLM(model="claude-sonnet-5", client=client)
    assert llm.translate("Hallo", "de") == "Translated"
    tags = llm.classify("T", "text", CATEGORIES)
    assert tags == (CategoryTag("dogs", 0.8),)
    assert client.messages.calls[0]["model"] == "claude-sonnet-5"
