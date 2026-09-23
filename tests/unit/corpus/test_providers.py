import json

import pytest

from swiss_grounding.corpus.providers import (
    INDEXES,
    FakeEmbeddings,
    FakeLLM,
    OpenAILLM,
    Usage,
    extract_json,
)


def test_index_registry_matches_the_schema():
    assert INDEXES["openai-3l"].dim == 3072 and INDEXES["openai-3l"].table == "corpus.emb_openai_3l"
    assert INDEXES["bge-m3"].dim == 1024 and INDEXES["bge-m3"].table == "corpus.emb_bge_m3"


def test_fake_embeddings_have_the_index_dimension():
    vectors = FakeEmbeddings(3072).embed(["Hund", "chien"])
    assert len(vectors) == 2 and vectors[0].shape == (3072,)


def test_top_sparse_keeps_the_heaviest_positive_terms():
    from swiss_grounding.corpus.providers import top_sparse
    weights = {"12": 0.1, "7": 0.9, "3": 0.0, "44": 0.5}
    assert top_sparse(weights, limit=2) == {7: 0.9, 44: 0.5}


def test_extract_json_tolerates_fences():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_fake_llm_calls_the_responder():
    llm = FakeLLM(lambda task: {"echo": task.custom_id})
    from swiss_grounding.corpus.runner import LlmTask
    data, usage = llm.complete(LlmTask("t1", "m", "sys", "user"))
    assert data == {"echo": "t1"} and isinstance(usage, Usage)


def test_openai_chat_body_uses_json_mode_and_minimal_reasoning():
    from swiss_grounding.corpus.runner import LlmTask
    body = OpenAILLM.chat_body(LlmTask("t", "gpt-5-nano", "sys", "user", image_png_b64="AAAA", max_output_tokens=500))
    assert body["response_format"] == {"type": "json_object"}
    assert body["reasoning_effort"] == "minimal"
    assert body["max_completion_tokens"] == 500
    content = body["messages"][1]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    json.dumps(body)
