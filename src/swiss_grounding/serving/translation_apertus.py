"""Query and passage translation through Apertus, as an alternative to Supertext (TRANSLATOR=apertus).

Same contract as SupertextTranslator: never raises into a search; any failure is logged and answered
with None, and the search goes on untranslated.
"""
import json
import logging
import threading
from collections import OrderedDict
from collections.abc import Mapping, Sequence

from swiss_grounding.corpus.providers import LLMProvider
from swiss_grounding.corpus.runner import LlmTask
from swiss_grounding.serving.translation import (
    CACHE_SIZE,
    MAX_CHARS_PER_REQUEST,
    Translation,
    batches,
    our_code,
)

log = logging.getLogger(__name__)

LANGUAGE_NAMES: Mapping[str, str] = {
    "de": "Swiss Standard German (Swiss spelling, ss instead of ß)",
    "fr": "French as written in Switzerland",
    "it": "Italian as written in Switzerland",
    "rm": "Romansh (Rumantsch Grischun)",
    "en": "British English",
}
SYSTEM = ("You translate short texts for a Swiss public-information search service. Keep legal references, "
          "names, numbers and URLs unchanged. Reply with JSON only.")
PROMPT = """Translate each text into {language}. Also give the two-letter ISO 639-1 code of the language the
texts are written in. Reply as {{"source_lang": "de", "translations": ["..."]}} with exactly {count}
translations, in the same order.

Texts:
{texts}"""
OUTPUT_TOKENS_FLOOR = 200
CHARS_PER_OUTPUT_TOKEN = 2      # generous: a translation can be longer than its source


class ApertusTranslator:
    name = "apertus"

    def __init__(self, llm: LLMProvider, cache_size: int = CACHE_SIZE):
        self._llm = llm
        self._cache: OrderedDict[tuple, Translation] = OrderedDict()
        self._cache_size = cache_size
        self._lock = threading.Lock()

    def translate(self, texts: Sequence[str], *, target: str, source: str | None) -> Translation | None:
        if target not in LANGUAGE_NAMES or not texts:
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
                return hit
        out = self._call(texts, target)
        if out is None:
            return None
        with self._lock:
            self._cache[key] = out
            while len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
        return out

    def _call(self, texts: list[str], target: str) -> Translation | None:
        chars = sum(len(t) for t in texts)
        task = LlmTask(custom_id="translate", model="apertus", system=SYSTEM,
                       user=PROMPT.format(language=LANGUAGE_NAMES[target], count=len(texts),
                                          texts=json.dumps(texts, ensure_ascii=False)),
                       max_output_tokens=OUTPUT_TOKENS_FLOOR + chars // CHARS_PER_OUTPUT_TOKEN)
        try:
            reply, _usage = self._llm.complete(task)
        except Exception as exc:  # noqa: BLE001 - a translator never raises into a search
            log.warning("apertus translate: call failed for target %s: %s: %s", target, type(exc).__name__, exc)
            return None
        translations = reply.get("translations")
        if (not isinstance(translations, list) or len(translations) != len(texts)
                or not all(isinstance(t, str) for t in translations)):
            log.warning("apertus translate: reply for target %s did not hold %d translations", target, len(texts))
            return None
        source_lang = reply.get("source_lang")
        return Translation(tuple(translations), our_code(source_lang if isinstance(source_lang, str) else None))
