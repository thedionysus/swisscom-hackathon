from dataclasses import dataclass

from swiss_grounding.ingest.errors import EnrichmentError
from swiss_grounding.ingest.models import ChunkDraft, Section

SENTENCE_BREAK = ". "


@dataclass(frozen=True)
class ChunkLimits:
    max_chars: int = 1500
    overlap_chars: int = 150

    def __post_init__(self) -> None:
        if self.max_chars <= 0 or self.overlap_chars < 0 or self.overlap_chars >= self.max_chars:
            raise ValueError("overlap_chars must be >= 0 and smaller than max_chars (> 0)")


def _split(text: str, limits: ChunkLimits) -> tuple[str, ...]:
    """Split on sentence-ish boundaries so pieces stay under max_chars, with a small overlap."""
    if len(text) <= limits.max_chars:
        return (text,)
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + limits.max_chars)
        if end < len(text):
            cut = text.rfind(SENTENCE_BREAK, start, end)
            if cut > start + limits.max_chars // 2:
                end = cut + 1
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - limits.overlap_chars, start + 1)
    return tuple(p for p in pieces if p)


def chunk_sections(
    original: tuple[Section, ...], english: tuple[Section, ...], limits: ChunkLimits,
) -> tuple[ChunkDraft, ...]:
    """Structure-aware chunking: one chunk per section, split only when the English exceeds the cap.

    The original-language text is attached whole to every piece of a split section, because the
    citation quotes the original and article boundaries are what matter there. Every piece of
    such a section is marked `original_is_parallel=False`, because that same whole original is
    not the original *of the piece*: read as a pair with the English, piece seven of nine sits
    beside the opening of the section. Only a caller reading the two together needs to know, and
    only the flag tells it.

    A section that has text in the original but none in English lost it in translation. That is an
    error, not a chunk to skip: the section count still matches, so nothing downstream would notice
    the document is missing an article.

    The drafts come back with no `context_en` and no `topics`. Both are decided per chunk by
    `ingest/context.py`, which is where the model calls of ADR 0005 live; splitting text is pure
    and stays that way, so it can be tested without a model and run without spending anything.
    """
    if len(original) != len(english):
        raise ValueError(f"section count mismatch: {len(original)} original vs {len(english)} english")
    drafts: list[ChunkDraft] = []
    for orig, en in zip(original, english, strict=True):
        text_en = en.text.strip()
        if not text_en:
            if orig.text.strip():
                raise EnrichmentError(f"section {en.heading_path!r} has no English text to chunk")
            continue
        pieces = _split(text_en, limits)
        for piece in pieces:
            drafts.append(ChunkDraft(
                ordinal=len(drafts), heading_path=en.heading_path, anchor=en.anchor,
                text_original=orig.text.strip(), text_en=piece,
                original_is_parallel=len(pieces) == 1,
            ))
    return tuple(drafts)
