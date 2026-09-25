import json
from types import SimpleNamespace

import pytest

from swiss_grounding.corpus.providers import (
    INDEXES,
    ApertusLLM,
    FakeEmbeddings,
    FakeLLM,
    OpenAILLM,
    ReplyError,
    Usage,
    extract_json,
)
from swiss_grounding.corpus.runner import LlmTask


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


def test_extract_json_rejects_non_dict_json():
    with pytest.raises(ValueError):
        extract_json("[1, 2, 3]")


def test_local_bge_m3_embed_with_sparse_of_no_texts_returns_empty_without_touching_the_model():
    from swiss_grounding.corpus.providers import LocalBgeM3
    bare = object.__new__(LocalBgeM3)  # skip __init__: no model load, no disk/network use
    assert bare.embed_with_sparse([]) == []


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


def test_openai_llm_raises_reply_error_but_keeps_billed_usage():
    from swiss_grounding.corpus.providers import ReplyError
    from swiss_grounding.corpus.runner import LlmTask

    llm = OpenAILLM(api_key="test")

    class FakeMessage:
        content = "not json"

    class FakeChoice:
        message = FakeMessage()
        finish_reason = "stop"

    class FakeUsage:
        prompt_tokens = 11
        completion_tokens = 3

    class FakeResponse:
        choices = (FakeChoice(),)
        usage = FakeUsage()

    llm._client.chat.completions.create = lambda **kwargs: FakeResponse()
    with pytest.raises(ReplyError) as exc_info:
        llm.complete(LlmTask("t", "gpt-5-nano", "s", "u"))
    assert exc_info.value.usage == Usage(11, 3)
    assert exc_info.value.finish_reason == "stop"


def test_anthropic_llm_complete_sends_the_expected_request_shape():
    from swiss_grounding.corpus.providers import AnthropicLLM
    from swiss_grounding.corpus.runner import LlmTask

    llm = AnthropicLLM(api_key="test", model="claude-x")
    calls = []

    class FakeBlock:
        type = "text"
        text = '{"ok": true}'

    class FakeUsage:
        input_tokens = 5
        output_tokens = 2

    class FakeResponse:
        content = (FakeBlock(),)
        stop_reason = "end_turn"
        usage = FakeUsage()

    def create(**kwargs):
        calls.append(kwargs)
        return FakeResponse()

    llm._client.messages.create = create
    task = LlmTask("t", "claude-x", "sys prompt", "describe this", image_png_b64="QQBB", max_output_tokens=600)
    data, usage = llm.complete(task)

    assert data == {"ok": True} and usage.input_tokens == 5 and usage.output_tokens == 2
    assert len(calls) == 1
    kwargs = calls[0]
    assert kwargs["model"] == "claude-x"
    assert kwargs["max_tokens"] == 600
    assert kwargs["system"] == "sys prompt"
    content = kwargs["messages"][0]["content"]
    assert content[0] == {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "QQBB"}}
    assert content[1] == {"type": "text", "text": "describe this"}


def test_anthropic_llm_raises_reply_error_but_keeps_billed_usage():
    from swiss_grounding.corpus.providers import AnthropicLLM, ReplyError
    from swiss_grounding.corpus.runner import LlmTask

    llm = AnthropicLLM(api_key="test", model="claude-x")

    class FakeBlock:
        type = "text"
        text = "not json"

    class FakeUsage:
        input_tokens = 21
        output_tokens = 4

    class FakeResponse:
        content = (FakeBlock(),)
        stop_reason = "end_turn"
        usage = FakeUsage()

    llm._client.messages.create = lambda **kwargs: FakeResponse()
    with pytest.raises(ReplyError) as exc_info:
        llm.complete(LlmTask("t", "claude-x", "s", "u"))
    assert exc_info.value.usage == Usage(21, 4)
    assert exc_info.value.finish_reason == "end_turn"


class _FakeChat:
    def __init__(self, content: str):
        self.calls: list[dict] = []
        self._content = content
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **body):
        self.calls.append(body)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._content), finish_reason="stop")],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20))


TASK = LlmTask(custom_id="c", model="gpt-5-nano", system="sys", user="hello", max_output_tokens=300)


def test_apertus_sends_its_own_model_json_mode_and_max_tokens():
    fake = _FakeChat('{"ok": true}')
    llm = ApertusLLM("k", base_url="https://x/v1", model="swiss-ai/Apertus-v1.5-70B", client=fake)
    reply, usage = llm.complete(TASK)
    [body] = fake.calls
    assert body["model"] == "swiss-ai/Apertus-v1.5-70B"
    assert body["response_format"] == {"type": "json_object"} and body["max_tokens"] == 300
    assert "reasoning_effort" not in body and "max_completion_tokens" not in body
    assert body["messages"] == [{"role": "system", "content": "sys"}, {"role": "user", "content": "hello"}]
    assert reply == {"ok": True} and usage == Usage(100, 20)


def test_apertus_sends_an_image_as_image_url():
    fake = _FakeChat('{"text": "x"}')
    llm = ApertusLLM("k", base_url="https://x/v1", model="m", client=fake)
    llm.complete(LlmTask(custom_id="ocr|1", model="m", system="s", user="u", image_png_b64="QUJD"))
    content = fake.calls[0]["messages"][1]["content"]
    assert content[1] == {"type": "image_url", "image_url": {"url": "data:image/png;base64,QUJD"}}


def test_apertus_unparseable_reply_keeps_the_billed_usage():
    llm = ApertusLLM("k", base_url="https://x/v1", model="m", client=_FakeChat("not json"))
    with pytest.raises(ReplyError) as exc:
        llm.complete(TASK)
    assert exc.value.usage == Usage(100, 20) and exc.value.finish_reason == "stop"


def test_the_pacer_spaces_starts_by_the_tighter_token_budget():
    from swiss_grounding.corpus.providers import RequestPacer
    now = [100.0]
    slept = []

    def sleep(seconds):
        slept.append(round(seconds, 3))
        now[0] += seconds
    pacer = RequestPacer(60_000, 6_000, clock=lambda: now[0], sleep=sleep)
    for _ in range(3):
        pacer.wait(1_000, 300)       # output is tighter: 300 of 100 per second = 3 s apart
    assert slept == [3.0, 3.0]


def test_an_unpaced_pacer_never_sleeps():
    from swiss_grounding.corpus.providers import RequestPacer
    slept = []
    pacer = RequestPacer(0.0, 0.0, clock=lambda: 5.0, sleep=slept.append)
    pacer.wait(1_000, 300)
    pacer.wait(1_000, 300)
    assert slept == []
