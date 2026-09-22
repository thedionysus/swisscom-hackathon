import json
import logging
import re
from collections.abc import Sequence
from typing import Any, Protocol

from swiss_grounding.ingest.errors import EnrichmentError
from swiss_grounding.ingest.models import CategoryTag, ChunkContext
from swiss_grounding.registry.categories import Category

log = logging.getLogger(__name__)

MAX_TOKENS = 4096
FAKE_KEYWORD_CONFIDENCE = 0.9
# One document excerpt reaches the summariser, and the summary is what every chunk call repeats.
# 6000 characters is a few pages: enough to say what an act is, short enough that the one call
# that pays for it stays small.
MAX_SUMMARY_CHARS = 6000
# The original wording is sent so a term with no English cognate can be kept, not so the model
# can read the section whole; one chunk's worth of it is the most that can serve that purpose.
MAX_ORIGINAL_CHARS = 1500
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0
MAX_ERROR_CHARS = 200
# FakeLLM only: shorter words are rarely the compound a translation had to give up on.
MIN_TERM_CHARS = 5
MAX_TITLE_CHARS = 120
FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
# The outermost {...}: a model that wraps its JSON in "Here is the JSON:" and a sign-off
# has answered, and greedy matching takes the whole object rather than a nested one.
JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
# One resample of a description before the document is abandoned. See `describe`.
DESCRIBE_ATTEMPTS = 2

TRANSLATE_PROMPT = (
    "Translate the following {language} text to English. Preserve paragraph breaks, numbering, "
    "article references and proper nouns. Output only the translation.\n\n{text}"
)
SUMMARISE_PROMPT = (
    "In one or two sentences, say what this document is -- the act, regulation, page or feed it "
    "is -- and what it covers. Name it explicitly rather than referring to 'this document'. Keep "
    "any Swiss or German term that has no English equivalent, spelled as in the original. "
    "Output only those sentences.\n\nTitle: {title}\n\nText:\n{text}"
)
DESCRIBE_PROMPT = (
    "You are writing a retrieval hint for one chunk of a document. It is indexed alongside the "
    "chunk so the chunk can be found, and it is never shown to a reader as a quotation.\n"
    'Reply with JSON only: {{"context": "...", "categories": [{{"id": "...", '
    '"confidence": 0.0-1.0}}], "boilerplate": true|false}}\n'
    '- "context": one or two sentences saying which document this chunk comes from and what this '
    "chunk itself covers. Keep any term from the original wording that has no English equivalent, "
    "spelled as in the original. Do not quote the chunk back.\n"
    '- "categories": every one of the categories below that this chunk is about, and none that it '
    "is not.\n"
    '- "boilerplate": true when the chunk is page furniture -- a navigation menu, a list of links, '
    "a postal address, opening hours, a cookie or accessibility notice, an error page -- rather "
    "than substance a question could be answered from.\n"
    "Always include all three keys. Use an empty list for categories when none applies, rather "
    "than leaving the key out, and true or false unquoted for boilerplate. Reply with the JSON "
    "object alone: no preamble, no explanation, no code fence.\n\n"
    "Categories:\n{categories}\n\n"
    "Document: {summary}\n\nSection heading: {heading}\n\n"
    "Chunk (English):\n{text_en}\n\nChunk (original wording):\n{text_original}"
)
# What stands where the original wording would be for a chunk that has none of its own. Said
# rather than left blank, so the model does not read silence as "this chunk had no original".
NO_PARALLEL_ORIGINAL = (
    "unavailable -- this chunk is one piece of a longer section, and the section's original "
    "wording does not line up with it. Work from the English alone."
)


class LLM(Protocol):
    def translate(self, text: str, source_language: str) -> str: ...
    def summarise(self, title_en: str, text_en: str) -> str: ...
    def describe(self, summary_en: str, heading_path: str, text_en: str, text_original: str | None,
                 categories: Sequence[Category]) -> ChunkContext: ...


def _confidence(item: dict[str, Any]) -> float:
    """How sure the model says it is, clamped to [0, 1].

    A tag with no stated confidence is malformed output, not a zero-confidence tag: confidence is
    dropped at persistence, so such a tag would be stored as a full-strength topic, and a topic is
    about to become a hard filter. We do not invent a constraint the model never asserted.

    The error names the tag rather than the response, because the offending one may sit past any
    truncation of it.
    """
    stated = item.get("confidence")
    try:
        if isinstance(stated, bool):  # bool is an int, and float(True) is full confidence
            raise TypeError("a boolean is not a confidence")
        value = float(stated)
    except (TypeError, ValueError) as exc:
        raise EnrichmentError(
            f"tag {item.get('id')!r} states no usable confidence: {str(stated)[:MAX_ERROR_CHARS]!r}") from exc
    return min(MAX_CONFIDENCE, max(MIN_CONFIDENCE, value))


def _tags(items: Any, known_ids: Sequence[str]) -> tuple[CategoryTag, ...]:
    """Read a decoded `categories` list; unknown ids dropped, confidence clamped to [0, 1].

    An unknown id is discarded before its confidence is read: it is a well-formed item naming a
    category outside our vocabulary, it cannot reach storage either way, and it is no reason to
    fail the document. Malformed structure raises, because an item that is not an object is the
    model ignoring the response format -- and read as an empty answer it would quietly hand the
    chunk its source's declared categories.
    """
    if not isinstance(items, list):
        raise EnrichmentError(f"categories is {type(items).__name__}, not a list")
    tags = []
    for item in items:
        if not isinstance(item, dict):
            raise EnrichmentError(f"tag is {type(item).__name__}, not an object")
        if item.get("id") in known_ids:
            tags.append(CategoryTag(id=item["id"], confidence=_confidence(item)))
    return tuple(tags)


def _decode(raw: str, call: str) -> dict[str, Any]:
    """Read the response as a JSON object, or fail saying which call and what came back.

    Prose around the object is tolerated. A preamble is the model being chatty, not the model
    refusing, and one chatty reply should not discard the hundred-odd paid calls already made
    for the document it belongs to. Output with no object in it at all still fails.
    """
    cleaned = FENCE_RE.sub("", raw.strip())
    found = JSON_OBJECT_RE.search(cleaned)
    try:
        if found is None:
            raise ValueError("no JSON object in the response")
        body = json.loads(found.group())
        if not isinstance(body, dict):
            raise TypeError(f"response is {type(body).__name__}, not an object")
    except (ValueError, TypeError) as exc:
        raise EnrichmentError(
            f"unparseable response for {call}: {raw[:MAX_ERROR_CHARS]!r}") from exc
    return body


def _boilerplate_verdict(body: dict[str, Any]) -> bool:
    """The model's page-furniture verdict, which must be a real boolean.

    Truthiness reads this answer backwards: `bool("false")` is True and `bool(0)` is False, and a
    missing key read as False indexes navigation menus as evidence. This is the mirror image of
    `_confidence` refusing a boolean, and deliberately does not reuse it -- there a boolean is the
    wrong type, here it is the only right one.
    """
    stated = body.get("boilerplate")
    if not isinstance(stated, bool):
        raise EnrichmentError(
            f"no usable boilerplate verdict: {str(stated)[:MAX_ERROR_CHARS]!r}")
    return stated


def _context(body: dict[str, Any]) -> str:
    """The generated description, required for every chunk that will actually be stored."""
    stated = body.get("context", "")
    if not isinstance(stated, str):
        raise EnrichmentError(f"no usable context: {str(stated)[:MAX_ERROR_CHARS]!r}")
    context = stated.strip()
    if not context:
        raise EnrichmentError("the model returned no context for a chunk it kept")
    return context


def _categories(body: dict[str, Any]) -> Any:
    """The `categories` entry, which the model must actually send.

    `[]` is an answer -- the model saying none apply -- and omitting the key is not the same
    statement: it is the model ignoring the response format. The difference decides whether a
    source's declared categories stand in for this chunk (`context.merge_topics`), so reading
    silence as "none named" would hand a chunk a topic on the strength of a key that was never
    there.
    """
    try:
        return body["categories"]
    except KeyError as exc:
        raise EnrichmentError("the model named no categories key at all") from exc


def parse_description(raw: str, known_ids: Sequence[str], call: str = "a description") -> ChunkContext:
    """Parse the JSON description response into context, topics and a boilerplate verdict.

    A chunk judged boilerplate is discarded, so nothing but that verdict is ever read from it and
    nothing but that verdict is required of it. Validating the rest would let a chunk already on
    its way to the bin fail the whole document, losing the articles around it -- which is the
    opposite of what this exemption is for. The verdict itself is validated as strictly as ever.
    """
    body = _decode(raw, call)
    if _boilerplate_verdict(body):
        return ChunkContext(context_en="", topics=(), boilerplate=True)
    return ChunkContext(
        context_en=_context(body),
        topics=_tags(_categories(body), known_ids),
        boilerplate=False,
    )


def _untranslated_term(text_en: str, text_original: str) -> str:
    """The longest word of the original that the English does not carry, or "".

    FakeLLM's stand-in for the instruction the real prompt gives: keep a term with no English
    equivalent, so `Grüngutabfuhr` stays reachable in an English index. Identity translation makes
    this empty for most fixtures, which keeps the fake's output close to the text it describes.
    """
    missing = [w for w in re.findall(r"\w+", text_original)
               if len(w) >= MIN_TERM_CHARS and w.lower() not in text_en.lower()]
    return max(missing, key=len, default="")


class FakeLLM:
    """Deterministic stand-in: identity translation, keyword-based topics. Tests and offline demos."""

    def translate(self, text: str, source_language: str) -> str:
        return text

    def summarise(self, title_en: str, text_en: str) -> str:
        return f"the document {title_en!r}"

    def describe(self, summary_en: str, heading_path: str, text_en: str, text_original: str | None,
                 categories: Sequence[Category]) -> ChunkContext:
        term = _untranslated_term(text_en, text_original or "")
        context = f"From {summary_en}. This section covers {heading_path}."
        if term:
            context += f" Original term: {term}."
        return ChunkContext(
            context_en=context,
            topics=self._keyword_tags(f"{heading_path} {text_en}", categories),
            boilerplate=False,      # the fake judges no furniture; the heading rules do that
        )

    @staticmethod
    def _keyword_tags(haystack: str, categories: Sequence[Category]) -> tuple[CategoryTag, ...]:
        lowered = haystack.lower()
        tags = []
        for c in categories:
            words = {c.id, *c.label.lower().split(), *c.description.lower().replace(",", " ").split()}
            keywords = {w for w in words if len(w) > 3}
            if any(k in lowered for k in keywords):
                tags.append(CategoryTag(id=c.id, confidence=FAKE_KEYWORD_CONFIDENCE))
        return tuple(tags)


class AnthropicLLM:
    """The real model. `messages_sent` counts what was actually put on the wire.

    A description that cannot be parsed is resampled (`DESCRIBE_ATTEMPTS`), so one chunk can cost
    two messages, and a backfill that billed one call per chunk would understate what it spent.
    The counter is what `recontext` bills from; it counts a message it set out to send, whether or
    not the reply was usable.
    """

    def __init__(self, model: str, client: Any):
        self._model = model
        self._client = client
        self.messages_sent = 0

    @classmethod
    def from_api_key(cls, model: str, api_key: str) -> "AnthropicLLM":
        from anthropic import Anthropic

        return cls(model=model, client=Anthropic(api_key=api_key))

    def _ask(self, prompt: str, call: str) -> str:
        """Ask the model and return its text, refusing a reply that carries none.

        An empty reply is a failure, not an answer: returned as an empty string it would become an
        empty title, or a section silently dropped from a document, with nothing recording that the
        model said nothing at all. `call` says which call it was, in the caller's own terms -- a
        slice of the prompt would be mostly the constant instructions, and the rest source text an
        operator has no use for in a log.
        """
        self.messages_sent += 1
        message = self._client.messages.create(
            model=self._model, max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(getattr(block, "text", "") for block in message.content).strip()
        if not text:
            raise EnrichmentError(f"the model returned no text for {call}")
        return text

    def translate(self, text: str, source_language: str) -> str:
        return self._ask(TRANSLATE_PROMPT.format(language=source_language, text=text),
                         call=f"a translation from {source_language} of {len(text)} characters")

    def summarise(self, title_en: str, text_en: str) -> str:
        """One call per document: what its chunks all say they come from.

        An untitled document is refused rather than summarised. Every chunk of the document
        repeats this summary, so one built from a blank title would assert, N times over, a
        subject nothing established -- and there is a stored Fedlex document with exactly that.
        """
        if not title_en.strip():
            raise EnrichmentError("cannot summarise a document with no title")
        return self._ask(
            SUMMARISE_PROMPT.format(title=title_en, text=text_en[:MAX_SUMMARY_CHARS]),
            call=f"the summary of {title_en[:MAX_TITLE_CHARS]!r}",
        )

    def describe(self, summary_en: str, heading_path: str, text_en: str, text_original: str | None,
                 categories: Sequence[Category]) -> ChunkContext:
        """One call per chunk: its context, its topics and whether it is page furniture.

        Resampled once if the reply cannot be read. A model's output is not deterministic, so a
        second sample is the cheapest recovery there is, and the alternative is losing every call
        already paid for in this document -- around a hundred and twelve of them for a Fedlex act,
        which is one transaction. The SDK's own retries cover transport; this covers the reply.
        """
        call = f"the description of chunk {heading_path[:MAX_TITLE_CHARS]!r}"
        prompt = self._describe_prompt(summary_en, heading_path, text_en, text_original, categories)
        known_ids = tuple(c.id for c in categories)
        for attempt in range(1, DESCRIBE_ATTEMPTS + 1):
            try:
                return parse_description(self._ask(prompt, call=call), known_ids, call=call)
            except EnrichmentError as exc:
                if attempt == DESCRIBE_ATTEMPTS:
                    raise
                log.warning("resampling %s after an unusable reply: %s", call, exc)
        raise AssertionError("unreachable: the final attempt either returns or raises")

    @staticmethod
    def _describe_prompt(summary_en: str, heading_path: str, text_en: str,
                         text_original: str | None, categories: Sequence[Category]) -> str:
        listing = "\n".join(f"- {c.id}: {c.label} ({c.description})" for c in categories)
        original = NO_PARALLEL_ORIGINAL if text_original is None else text_original[:MAX_ORIGINAL_CHARS]
        return DESCRIBE_PROMPT.format(categories=listing, summary=summary_en, heading=heading_path,
                                      text_en=text_en, text_original=original)


def build_llm(backend: str, model: str, api_key: str | None) -> LLM:
    if backend == "fake":
        return FakeLLM()
    if backend == "anthropic":
        if not api_key:
            raise ValueError("anthropic backend requires an api key")
        return AnthropicLLM.from_api_key(model=model, api_key=api_key)
    raise ValueError(f"unknown llm backend: {backend}")
