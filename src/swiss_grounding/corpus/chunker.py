import re

from swiss_grounding.corpus.models import ChunkDraft, ParsedDocument, ParsedSection

MAX_CHARS = 1800
HARD_MAX_CHARS = 3000
OVERLAP_CHARS = 150

# Legal abbreviations that end in a period but are never a sentence end. Checked case-sensitively
# against the word immediately preceding the matched punctuation.
_ABBREVIATIONS = frozenset({
    "Art", "Abs", "lit", "Ziff", "Nr", "z", "B", "bzw", "vgl", "al", "cf", "ch", "cpv", "cap",
})

# A sentence end: closing punctuation followed by whitespace and an uppercase/digit start of the
# next sentence, or a period at the end of a line.
_SENTENCE_END_RE = re.compile(r"[.!?:;]\s+(?=[A-ZÄÖÜÀ-Ý0-9])|\.\n")


def _is_abbreviation(text: str, punct_pos: int, start: int) -> bool:
    """True when the word right before text[punct_pos] (the punctuation) is a known abbreviation."""
    word_start = punct_pos
    while word_start > start and text[word_start - 1].isalpha():
        word_start -= 1
    return text[word_start:punct_pos] in _ABBREVIATIONS


def _find_cut(text: str, start: int, end: int) -> int | None:
    """Index right after the best sentence-ending punctuation in text[start:end], or None."""
    best = None
    for m in _SENTENCE_END_RE.finditer(text, start, end):
        punct_pos = m.start()
        if _is_abbreviation(text, punct_pos, start):
            continue
        best = punct_pos + 1
    return best


def _windows(text: str) -> list[str]:
    """Cut `text` into pieces of at most MAX_CHARS, preferring a sentence end, overlapping by OVERLAP_CHARS."""
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + MAX_CHARS, len(text))
        if end < len(text):
            cut = _find_cut(text, start, end)
            if cut is not None and cut > start + MAX_CHARS // 2:
                end = cut
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        next_start = end - OVERLAP_CHARS
        # don't start the next window mid-word: advance to just after the next whitespace
        ws = text.find(" ", next_start, end)
        if ws != -1:
            next_start = ws + 1
        start = max(next_start, start + 1)
    return pieces


def _units(section: ParsedSection) -> list[tuple[str, str]]:
    """(align_key, text) units for one section, before numbering."""
    text = section.text.strip()
    split_paragraphs = bool(section.paragraphs) and (len(text) > MAX_CHARS or section.split_paragraphs)
    if not split_paragraphs:
        if len(text) <= MAX_CHARS:
            return [(section.align_key, text)]
        return [(f"{section.align_key}#{i}", w) for i, w in enumerate(_windows(text))]
    units: list[tuple[str, str]] = []
    for key, para in section.paragraphs:
        para = para.strip()
        if len(para) <= HARD_MAX_CHARS:
            units.append((key, para))
        else:
            units.extend((f"{key}#{i}", w) for i, w in enumerate(_windows(para)))
    return units


def chunk_document(doc: ParsedDocument) -> tuple[ChunkDraft, ...]:
    drafts: list[ChunkDraft] = []
    for section in doc.sections:
        if section.needs_ocr:
            drafts.append(ChunkDraft(align_key=section.align_key, ordinal=len(drafts), breadcrumb=section.breadcrumb,
                                     anchor=section.anchor, text="", needs_ocr=True, ocr_image=section.ocr_image,
                                     ocr_digest=section.ocr_digest))
            continue
        for key, text in _units(section):
            if text:
                drafts.append(ChunkDraft(align_key=key, ordinal=len(drafts), breadcrumb=section.breadcrumb,
                                         anchor=section.anchor, text=text))
    return tuple(drafts)
