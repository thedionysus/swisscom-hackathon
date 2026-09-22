import json
import re
from collections.abc import Sequence
from typing import Any, Protocol

from swiss_grounding.ingest.models import CategoryTag, EnrichmentError
from swiss_grounding.registry.categories import Category

MAX_TOKENS = 4096
FAKE_KEYWORD_CONFIDENCE = 0.9
MAX_CLASSIFY_CHARS = 6000
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0
MAX_ERROR_CHARS = 200
FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

TRANSLATE_PROMPT = (
    "Translate the following {language} text to English. Preserve paragraph breaks, numbering, "
    "article references and proper nouns. Output only the translation.\n\n{text}"
)
CLASSIFY_PROMPT = (
    "Classify the document below into zero or more of these categories. "
    'Reply with JSON only: {{"categories": [{{"id": "...", "confidence": 0.0-1.0}}]}}.\n'
    "Categories:\n{categories}\n\nTitle: {title}\n\nText:\n{text}"
)


class LLM(Protocol):
    def translate(self, text: str, source_language: str) -> str: ...
    def classify(self, title: str, text: str, categories: Sequence[Category]) -> tuple[CategoryTag, ...]: ...


def _confidence(item: Any, raw: str) -> float:
    """How sure the model says it is, clamped to [0, 1].

    A tag with no stated confidence is malformed output, not a zero-confidence tag: confidence is
    dropped at persistence, so such a tag would be stored as a full-strength topic, and a topic is
    about to become a hard filter. We do not invent a constraint the model never asserted.
    """
    try:
        value = float(item["confidence"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise EnrichmentError(f"tag without a usable confidence: {raw[:MAX_ERROR_CHARS]!r}") from exc
    return min(MAX_CONFIDENCE, max(MIN_CONFIDENCE, value))


def parse_tags(raw: str, known_ids: Sequence[str]) -> tuple[CategoryTag, ...]:
    """Parse the JSON tag response; unknown ids dropped, confidence clamped to [0, 1].

    An empty category list is an answer -- the model saying none apply -- and comes back as an empty
    tuple. Output that cannot be read as that answer raises instead, so a document with no usable
    tags is retried rather than falling through to its source's declared categories.
    """
    cleaned = FENCE_RE.sub("", raw.strip())
    try:
        items = json.loads(cleaned)["categories"]
        if not isinstance(items, list):
            raise TypeError(f"categories is {type(items).__name__}, not a list")
    except (ValueError, KeyError, TypeError) as exc:
        raise EnrichmentError(f"unparseable tag response: {raw[:MAX_ERROR_CHARS]!r}") from exc
    tags = []
    for item in items:
        confidence = _confidence(item, raw)
        cid = item.get("id")
        if cid in known_ids:
            tags.append(CategoryTag(id=cid, confidence=confidence))
    return tuple(tags)


class FakeLLM:
    """Deterministic stand-in: identity translation, keyword-based tags. Tests and offline demos."""

    def translate(self, text: str, source_language: str) -> str:
        return text

    def classify(self, title: str, text: str, categories: Sequence[Category]) -> tuple[CategoryTag, ...]:
        haystack = f"{title} {text}".lower()
        tags = []
        for c in categories:
            words = {c.id, *c.label.lower().split(), *c.description.lower().replace(",", " ").split()}
            keywords = {w for w in words if len(w) > 3}
            if any(k in haystack for k in keywords):
                tags.append(CategoryTag(id=c.id, confidence=FAKE_KEYWORD_CONFIDENCE))
        return tuple(tags)


class AnthropicLLM:
    def __init__(self, model: str, client: Any):
        self._model = model
        self._client = client

    @classmethod
    def from_api_key(cls, model: str, api_key: str) -> "AnthropicLLM":
        from anthropic import Anthropic

        return cls(model=model, client=Anthropic(api_key=api_key))

    def _ask(self, prompt: str) -> str:
        """Ask the model and return its text, refusing a reply that carries none.

        An empty reply is a failure, not an answer: returned as an empty string it would become an
        empty title, or a section silently dropped from a document, with nothing recording that the
        model said nothing at all.
        """
        message = self._client.messages.create(
            model=self._model, max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(getattr(block, "text", "") for block in message.content).strip()
        if not text:
            raise EnrichmentError(f"model returned no text for prompt: {prompt[:MAX_ERROR_CHARS]!r}")
        return text

    def translate(self, text: str, source_language: str) -> str:
        return self._ask(TRANSLATE_PROMPT.format(language=source_language, text=text))

    def classify(self, title: str, text: str, categories: Sequence[Category]) -> tuple[CategoryTag, ...]:
        listing = "\n".join(f"- {c.id}: {c.label} ({c.description})" for c in categories)
        raw = self._ask(CLASSIFY_PROMPT.format(categories=listing, title=title, text=text[:MAX_CLASSIFY_CHARS]))
        return parse_tags(raw, tuple(c.id for c in categories))


def build_llm(backend: str, model: str, api_key: str | None) -> LLM:
    if backend == "fake":
        return FakeLLM()
    if backend == "anthropic":
        if not api_key:
            raise ValueError("anthropic backend requires an api key")
        return AnthropicLLM.from_api_key(model=model, api_key=api_key)
    raise ValueError(f"unknown llm backend: {backend}")
