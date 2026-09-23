from swiss_grounding.corpus.models import ChunkDraft, ParsedDocument, ParsedSection

MAX_CHARS = 1800
HARD_MAX_CHARS = 3000
OVERLAP_CHARS = 150


def _windows(text: str) -> list[str]:
    """Cut `text` into pieces of at most MAX_CHARS, preferring a sentence end, overlapping by OVERLAP_CHARS."""
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + MAX_CHARS, len(text))
        if end < len(text):
            cut = text.rfind(". ", start, end)
            if cut > start + MAX_CHARS // 2:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        start = max(end - OVERLAP_CHARS, start + 1)
    return pieces


def _units(section: ParsedSection) -> list[tuple[str, str]]:
    """(align_key, text) units for one section, before numbering."""
    text = section.text.strip()
    if len(text) <= MAX_CHARS:
        return [(section.align_key, text)]
    if section.paragraphs:
        units: list[tuple[str, str]] = []
        for key, para in section.paragraphs:
            para = para.strip()
            if len(para) <= HARD_MAX_CHARS:
                units.append((key, para))
            else:
                units.extend((f"{key}#{i}", w) for i, w in enumerate(_windows(para)))
        return units
    return [(f"{section.align_key}#{i}", w) for i, w in enumerate(_windows(text))]


def chunk_document(doc: ParsedDocument) -> tuple[ChunkDraft, ...]:
    drafts: list[ChunkDraft] = []
    for section in doc.sections:
        if section.needs_ocr:
            drafts.append(ChunkDraft(align_key=section.align_key, ordinal=len(drafts), breadcrumb=section.breadcrumb,
                                     anchor=section.anchor, text="", needs_ocr=True, ocr_image=section.ocr_image))
            continue
        for key, text in _units(section):
            if text:
                drafts.append(ChunkDraft(align_key=key, ordinal=len(drafts), breadcrumb=section.breadcrumb,
                                         anchor=section.anchor, text=text))
    return tuple(drafts)
