"""Query and passage translation through Supertext (ADR 0018).

The server translates the question into the other language stores before searching, and the cited
passages back into the question's language after. A translator never raises into a search: every
failure is logged with its context and answered with None, and the search goes on as if no
translation were configured.
"""
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol

import httpx

from swiss_grounding.serving.models import LANGS

log = logging.getLogger(__name__)

# Supertext speaks BCP-47; Swiss variants keep Swiss spelling ("ss", Swiss French numerals). English
# needs a regional variant: bare "en" is refused as a target (INVALID_LANGUAGE_PAIR, checked 2026-09-24).
TARGET_CODES: Mapping[str, str] = {"de": "de-CH", "fr": "fr-CH", "it": "it-CH", "rm": "rm", "en": "en-GB"}
SUPPORTED: frozenset[str] = frozenset(LANGS)
assert SUPPORTED == frozenset(TARGET_CODES), "every language store needs a Supertext target code"
TRANSLATE_PATH = "/translate/ai/text"
AUTH_SCHEME = "Supertext-Auth-Key"
MAX_CHARS_PER_REQUEST = 9_000      # the service allows 10,000; headroom for JSON escaping
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
DEFAULT_RETRY_BACKOFF_SECONDS = 0.5
CACHE_SIZE = 2_048
MAX_PARALLEL_REQUESTS = 4          # the service allows 5 requests per second


@dataclass(frozen=True)
class Translation:
    texts: tuple[str, ...]
    source_lang: str | None       # our two-letter code, from the service's detection


class Translator(Protocol):
    name: str

    def translate(self, texts: Sequence[str], *, target: str, source: str | None) -> Translation | None: ...


class NoTranslator:
    """Configured when no key is present: the server behaves as before ADR 0018."""
    name = "none"

    def translate(self, texts: Sequence[str], *, target: str, source: str | None) -> Translation | None:
        return None


def our_code(bcp47: str | None) -> str | None:
    """'de-CH' -> 'de'; None for a language the corpus has no store for."""
    if not bcp47:
        return None
    code = bcp47.split("-", 1)[0].lower()
    return code if code in SUPPORTED else None


def batches(texts: Sequence[str], max_chars: int) -> list[list[str]]:
    """Consecutive runs of texts whose lengths sum to at most max_chars; order is kept."""
    out: list[list[str]] = []
    current: list[str] = []
    size = 0
    for text in texts:
        if current and size + len(text) > max_chars:
            out.append(current)
            current, size = [], 0
        current = [*current, text]
        size += len(text)
    return [*out, current] if current else out


class SupertextTranslator:
    """Supertext AI text translation: POST {base_url}/translate/ai/text with a batch of texts."""

    name = "supertext"

    def __init__(self, api_key: str, *, base_url: str, timeout_seconds: float,
                 transport: httpx.BaseTransport | None = None, cache_size: int = CACHE_SIZE,
                 retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS):
        self._client = httpx.Client(base_url=base_url, timeout=timeout_seconds, transport=transport,
                                    headers={"Authorization": f"{AUTH_SCHEME} {api_key}"})
        self._cache: OrderedDict[tuple, Translation] = OrderedDict()
        self._cache_size = cache_size
        self._backoff = retry_backoff_seconds
        self._lock = threading.Lock()

    def translate(self, texts: Sequence[str], *, target: str, source: str | None) -> Translation | None:
        if target not in TARGET_CODES or not texts:
            return None
        results = [self._batch(batch, target, source) for batch in batches(texts, MAX_CHARS_PER_REQUEST)]
        if any(r is None for r in results):
            return None
        detected = next((r.source_lang for r in results if r.source_lang), None)
        return Translation(tuple(t for r in results for t in r.texts), detected)

    def _batch(self, texts: list[str], target: str, source: str | None) -> Translation | None:
        key = (tuple(texts), target, source)
        with self._lock:
            hit = self._cache.get(key)
            if hit is not None:
                self._cache.move_to_end(key)
        if hit is not None:
            return hit
        body = {"text": texts, "target_lang": TARGET_CODES[target]}
        if source in TARGET_CODES:
            body["source_lang"] = source
        out = self._post(body)
        if out is None or len(out.texts) != len(texts):
            return None
        with self._lock:
            self._cache[key] = out
            while len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
        return out

    def close(self) -> None:
        self._client.close()

    def _post(self, body: dict) -> Translation | None:
        for attempt in range(2):
            try:
                response = self._client.post(TRANSLATE_PATH, json=body)
            except httpx.HTTPError as exc:
                log.warning("supertext: request failed for target %s: %s: %s", body["target_lang"],
                            type(exc).__name__, exc)
                return None
            if response.status_code in RETRY_STATUSES and attempt == 0:
                time.sleep(self._backoff)
                continue
            return _parse(response, body["target_lang"])
        return None


def _parse(response: httpx.Response, target: str) -> Translation | None:
    if response.status_code != 200:
        detail = _error_detail(response)
        log.warning("supertext: HTTP %s for target %s: %s", response.status_code, target, detail)
        return None
    try:
        data = response.json()
    except ValueError:
        log.warning("supertext: reply for target %s is not JSON", target)
        return None
    texts = data.get("translated_text") if isinstance(data, dict) else None
    if not isinstance(texts, list) or not all(isinstance(t, str) for t in texts):
        log.warning("supertext: reply for target %s has no translated_text list", target)
        return None
    return Translation(tuple(texts), our_code(data.get("detected_source_lang")))


def _error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(data, dict):
        return str(data.get("error_code") or data.get("message") or data.get("detail") or data)[:200]
    return str(data)[:200]


def safe_translate(translator: Translator, texts: Sequence[str], *, target: str,
                   source: str | None) -> Translation | None:
    """`translator.translate`, with any exception logged and answered as None: a translation
    problem never becomes an error status (ADR 0018)."""
    try:
        return translator.translate(texts, target=target, source=source)
    except Exception as exc:  # noqa: BLE001 - the translator is a plugin; nothing it raises may escape
        log.warning("translator %s failed for target %s (source %s): %s: %s", getattr(translator, "name", "?"),
                    target, source, type(exc).__name__, exc)
        return None


def translate_many(translator: Translator, jobs: Sequence[tuple[Sequence[str], str, str | None]],
                   ) -> list[Translation | None]:
    """One translation per (texts, target, source) job, in parallel, in the jobs' order."""
    if not jobs:
        return []
    with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_REQUESTS, len(jobs))) as pool:
        return list(pool.map(lambda j: safe_translate(translator, j[0], target=j[1], source=j[2]), jobs))


def fill_translations(translator: Translator, question: str, question_lang: str | None,
                      wanted: Sequence[str], *, have: Mapping[str, str]) -> tuple[dict[str, str], str | None]:
    """The question in every wanted language the client did not send, plus the detected language.

    The question's own language is never requested. When it is unknown, the first request goes
    alone, the language the service detected is read from its reply, and that store is skipped
    for the rest. Languages the service could not translate are left out, so the search runs with
    whatever was obtained. The remaining requests run in parallel."""
    targets = [lang for lang in wanted if lang in SUPPORTED and lang != question_lang and lang not in have]
    if isinstance(translator, NoTranslator) or not targets:
        return dict(have), None
    detected: str | None = None
    results: list[tuple[str, Translation | None]] = []
    if question_lang is None:
        first = safe_translate(translator, [question], target=targets[0], source=None)
        detected = first.source_lang if first is not None else None
        results.append((targets[0], first))
        targets = [t for t in targets[1:] if t != detected]
    source = question_lang or detected
    results.extend(zip(targets, translate_many(translator, [([question], t, source) for t in targets]),
                       strict=True))
    detected = detected or next((r.source_lang for _, r in results if r is not None and r.source_lang), None)
    filled = {target: r.texts[0] for target, r in results
              if r is not None and r.texts and target != (question_lang or detected)}
    return {**have, **filled}, detected
