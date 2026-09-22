"""Translate a fetched document to English and place it at an extent.

Enrichment used to classify the document as well, once, over a capped excerpt of it, and
`persist` copied that one tag set onto every chunk. ADR 0003 rejects that granularity --
a hundred-article act is not about one subject -- so the judgement moved to `context.py`, which
makes it per chunk. The document-level call went with it rather than being kept alongside: it
answered the same question at a granularity we no longer store, and would be a call per document
of pure waste on every ingest. A document's categories are now the roll-up of its chunks'.
"""

from swiss_grounding.ingest.llm import LLM
from swiss_grounding.ingest.models import EnrichedDocument, FetchedDocument, Section
from swiss_grounding.ingest.narrowing import SOURCE_DEFAULT, narrow_extent
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.models import Source

SECTION_SEPARATOR = "\n\n"
ENGLISH = "en"


def _translate_sections(doc: FetchedDocument, llm: LLM) -> tuple[Section, ...]:
    """Translate each section, leaving a section that has no text alone.

    This guard exists so that a blank section in the *source* never becomes an enrichment failure.
    A source-side blank is a source artifact, not a translation that came back empty, and failing a
    whole document over one would be the wrong response; the model is simply not asked to translate
    nothing. Chunking then skips it, and an empty reply to a section that did have text still fails
    the document, which is the case this pair of guards is really about. Do not delete this as
    redundant with the fetchers' own guards: it is what keeps the two cases distinguishable.
    """
    if doc.language == ENGLISH:
        return doc.sections
    return tuple(
        Section(heading_path=s.heading_path, anchor=s.anchor,
                text=llm.translate(s.text, doc.language) if s.text.strip() else s.text)
        for s in doc.sections
    )


def enrich(doc: FetchedDocument, source: Source, tree: LocationTree, llm: LLM) -> EnrichedDocument:
    """Translate to English and narrow the extent when the source allows it. No tagging: see above."""
    sections_en = _translate_sections(doc, llm)
    title_en = doc.title if doc.language == ENGLISH else llm.translate(doc.title, doc.language)
    if source.allow_narrowing:
        headings = tuple(s.heading_path for s in sections_en)
        text_en = SECTION_SEPARATOR.join(s.text for s in sections_en)
        extent_id, reason = narrow_extent(tree, source.default_extent_id, title_en, headings, text_en)
    else:
        extent_id, reason = source.default_extent_id, SOURCE_DEFAULT
    return EnrichedDocument(fetched=doc, title_en=title_en, sections_en=sections_en,
                            extent_id=extent_id, extent_reason=reason)


def document_text(doc: EnrichedDocument) -> str:
    """The document's English text in one string, for the one summary call its chunks share."""
    return SECTION_SEPARATOR.join(s.text for s in doc.sections_en)
