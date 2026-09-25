import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from swiss_grounding.corpus.runner import LlmTask
from swiss_grounding.retrieval.embedder import FakeEmbedder


@dataclass(frozen=True)
class IndexSpec:
    name: str
    provider: str
    model: str
    dim: int
    table: str
    opclass: str


INDEXES: dict[str, IndexSpec] = {
    "openai-3l": IndexSpec("openai-3l", "openai", "text-embedding-3-large", 3072, "corpus.emb_openai_3l",
                           "halfvec_cosine_ops"),
    "bge-m3": IndexSpec("bge-m3", "local", "BAAI/bge-m3", 1024, "corpus.emb_bge_m3", "vector_cosine_ops"),
}


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


class EmbeddingProvider(Protocol):
    dim: int

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]: ...


class FakeEmbeddings:
    def __init__(self, dim: int):
        self.dim = dim
        self._inner = FakeEmbedder(dim=dim)

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]:
        return self._inner.embed(texts)


class OpenAIEmbeddings:
    """Synchronous OpenAI embeddings, for `--sync` and small runs. Large runs use the Batch API."""
    dim = 3072

    def __init__(self, api_key: str, model: str = "text-embedding-3-large"):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self.model = model
        self.last_usage = 0

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]:
        response = self._client.embeddings.create(model=self.model, input=list(texts))
        self.last_usage = response.usage.prompt_tokens
        return [np.asarray(item.embedding, dtype=np.float32) for item in response.data]


BGE_M3_VOCAB = 250002
MAX_SPARSE_TERMS = 1000     # pgvector's HNSW limit on non-zero entries of a sparsevec
BGE_MAX_TOKENS = 2048       # breadcrumb + description + a long paragraph exceeds 1,024


def top_sparse(weights: dict, limit: int = MAX_SPARSE_TERMS) -> dict[int, float]:
    """bge-m3 lexical weights ({token_id: weight}) trimmed to the `limit` heaviest, keys as ints."""
    items = sorted(((int(k), float(v)) for k, v in weights.items() if float(v) > 0), key=lambda kv: -kv[1])
    return dict(items[:limit])


class LocalBgeM3:
    """bge-m3 on this machine: Apple GPU when available, else CPU.

    With FlagEmbedding installed it returns the dense vector and bge-m3's learned sparse vector from the
    same forward pass; without it, it falls back to sentence-transformers, dense only.
    """
    dim = 1024

    def __init__(self, model: str = "BAAI/bge-m3", batch_size: int = 16):
        import torch
        self._device = "mps" if torch.backends.mps.is_available() else "cpu"
        self._batch_size = batch_size
        try:
            from FlagEmbedding import BGEM3FlagModel
            self._flag = BGEM3FlagModel(model, use_fp16=False, devices=self._device)
            self._st = None
        except ImportError:
            from sentence_transformers import SentenceTransformer
            self._flag = None
            self._st = SentenceTransformer(model, device=self._device)
            self._st.max_seq_length = BGE_MAX_TOKENS

    @property
    def has_sparse(self) -> bool:
        return self._flag is not None

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]:
        return [dense for dense, _ in self.embed_with_sparse(texts)]

    def embed_with_sparse(self, texts: Sequence[str]) -> list[tuple[np.ndarray, dict[int, float] | None]]:
        if not texts:
            return []
        if self._flag is not None:
            out = self._flag.encode(list(texts), batch_size=self._batch_size, max_length=BGE_MAX_TOKENS,
                                    return_dense=True, return_sparse=True, return_colbert_vecs=False)
            return [(np.asarray(d, dtype=np.float32), top_sparse(s))
                    for d, s in zip(out["dense_vecs"], out["lexical_weights"], strict=True)]
        arr = self._st.encode(list(texts), batch_size=self._batch_size, normalize_embeddings=True)
        return [(np.asarray(row, dtype=np.float32), None) for row in arr]


def extract_json(text: str) -> dict:
    """The first JSON object in a model reply, tolerating code fences and trailing text."""
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object in model reply")
    try:
        value, _end = json.JSONDecoder().raw_decode(text, start)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in model reply: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("model reply is not a JSON object")  # noqa: TRY004 - a JSON parse-shape check
    return value


class ReplyError(RuntimeError):
    """A paid reply that could not be parsed as JSON. Carries the usage that was still billed
    (and the model's finish/stop reason, when available) so the caller can record spend even
    though the task failed."""

    def __init__(self, message: str, usage: Usage, finish_reason: str | None = None):
        super().__init__(message)
        self.usage = usage
        self.finish_reason = finish_reason


class LLMProvider(Protocol):
    def complete(self, task: LlmTask) -> tuple[dict, Usage]: ...


class FakeLLM:
    def __init__(self, responder: Callable[[LlmTask], dict]):
        self._responder = responder

    def complete(self, task: LlmTask) -> tuple[dict, Usage]:
        return self._responder(task), Usage(len(task.user) // 3, 50)


def chat_messages(task: LlmTask) -> list[dict]:
    """System + user messages in the OpenAI chat format; a page image travels as a data URL."""
    if task.image_png_b64:
        user_content: list | str = [
            {"type": "text", "text": task.user},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{task.image_png_b64}"}},
        ]
    else:
        user_content = task.user
    return [{"role": "system", "content": task.system}, {"role": "user", "content": user_content}]


def _parsed(text: str, usage: Usage, finish_reason: str | None) -> tuple[dict, Usage]:
    try:
        return extract_json(text), usage
    except ValueError as exc:
        raise ReplyError(f"unparseable reply: {exc}", usage, finish_reason) from exc


class OpenAILLM:
    def __init__(self, api_key: str, max_retries: int = 2):
        """`max_retries` also covers 429s: the client waits as the rate-limit headers ask."""
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key, max_retries=max_retries)

    @staticmethod
    def chat_body(task: LlmTask) -> dict:
        return {
            "model": task.model,
            "messages": chat_messages(task),
            "response_format": {"type": "json_object"},
            "max_completion_tokens": task.max_output_tokens,
            # gpt-5 models bill reasoning tokens as output; descriptions and OCR need none.
            "reasoning_effort": "minimal",
        }

    def complete(self, task: LlmTask) -> tuple[dict, Usage]:
        response = self._client.chat.completions.create(**self.chat_body(task))
        choice = response.choices[0]
        text = choice.message.content or ""
        usage = Usage(response.usage.prompt_tokens, response.usage.completion_tokens)
        return _parsed(text, usage, getattr(choice, "finish_reason", None))


class AnthropicLLM:
    """Synchronous fallback on Claude. The Batch path is OpenAI-only (OpenAI is the main provider)."""

    def __init__(self, api_key: str, model: str):
        from anthropic import Anthropic
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def complete(self, task: LlmTask) -> tuple[dict, Usage]:
        content: list[dict] = [{"type": "text", "text": task.user}]
        if task.image_png_b64:
            content.insert(0, {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                           "data": task.image_png_b64}})
        response = self._client.messages.create(model=self._model, max_tokens=task.max_output_tokens,
                                                system=task.system, messages=[{"role": "user", "content": content}])
        text = "".join(block.text for block in response.content if block.type == "text")
        usage = Usage(response.usage.input_tokens, response.usage.output_tokens)
        try:
            return extract_json(text), usage
        except ValueError as exc:
            raise ReplyError(f"unparseable reply: {exc}", usage, getattr(response, "stop_reason", None)) from exc


APERTUS_TEMPERATURE = 0.2   # descriptions and labels want steady wording, not variety


class ApertusLLM:
    """Apertus through an OpenAI-compatible endpoint (Swisscom's Swiss AI Platform). Direct calls only:
    the platform has no Batch API. The model is the configured one, whatever the task names (as with
    AnthropicLLM). `max_retries` also covers 429s from the 5 requests/s limit."""

    def __init__(self, api_key: str, *, base_url: str, model: str, timeout_seconds: float = 60.0,
                 max_retries: int = 2, client=None):
        if client is None:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds, max_retries=max_retries)
        self._client = client
        self.model = model

    def chat_body(self, task: LlmTask) -> dict:
        return {"model": self.model, "messages": chat_messages(task), "response_format": {"type": "json_object"},
                "max_tokens": task.max_output_tokens, "temperature": APERTUS_TEMPERATURE}

    def complete(self, task: LlmTask) -> tuple[dict, Usage]:
        response = self._client.chat.completions.create(**self.chat_body(task))
        choice = response.choices[0]
        usage = Usage(response.usage.prompt_tokens, response.usage.completion_tokens)
        return _parsed(choice.message.content or "", usage, getattr(choice, "finish_reason", None))
