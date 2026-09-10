import json
import re
from collections.abc import Sequence
from typing import Any, Protocol

from swiss_grounding.ingest.models import CategoryTag
from swiss_grounding.registry.categories import Category

MAX_TOKENS = 4096
FAKE_KEYWORD_CONFIDENCE = 0.9
MAX_CLASSIFY_CHARS = 6000
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


def parse_tags(raw: str, known_ids: Sequence[str]) -> tuple[CategoryTag, ...]:
    """Parse the JSON tag response; unknown ids dropped, confidence clamped to [0, 1]."""
    cleaned = FENCE_RE.sub("", raw.strip())
    try:
        data = json.loads(cleaned)
        items = data["categories"]
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"unparseable tag response: {raw[:200]!r}") from exc
    tags = []
    for item in items:
        cid = item.get("id")
        if cid in known_ids:
            confidence = min(1.0, max(0.0, float(item.get("confidence", 0.0))))
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
        message = self._client.messages.create(
            model=self._model, max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(getattr(block, "text", "") for block in message.content).strip()

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
