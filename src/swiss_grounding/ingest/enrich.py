from collections.abc import Sequence

from swiss_grounding.ingest.llm import LLM
from swiss_grounding.ingest.models import CategoryTag, EnrichedDocument, FetchedDocument, Section
from swiss_grounding.ingest.narrowing import SOURCE_DEFAULT, narrow_extent
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.categories import Category
from swiss_grounding.registry.models import Source

SOURCE_DEFAULT_CONFIDENCE = 1.0
SECTION_SEPARATOR = "\n\n"
ENGLISH = "en"


def _translate_sections(doc: FetchedDocument, llm: LLM) -> tuple[Section, ...]:
    if doc.language == ENGLISH:
        return doc.sections
    return tuple(
        Section(heading_path=s.heading_path, anchor=s.anchor, text=llm.translate(s.text, doc.language))
        for s in doc.sections
    )


def _merge_tags(defaults: Sequence[str], llm_tags: Sequence[CategoryTag]) -> tuple[CategoryTag, ...]:
    merged = {t.id: t for t in llm_tags}
    for cid in defaults:
        merged[cid] = CategoryTag(id=cid, confidence=SOURCE_DEFAULT_CONFIDENCE)
    return tuple(sorted(merged.values(), key=lambda t: (-t.confidence, t.id)))


def enrich(
    doc: FetchedDocument, source: Source, tree: LocationTree, llm: LLM, categories: Sequence[Category],
) -> EnrichedDocument:
    """Translate to English, tag categories, and narrow the extent when the source allows it."""
    sections_en = _translate_sections(doc, llm)
    title_en = doc.title if doc.language == ENGLISH else llm.translate(doc.title, doc.language)
    text_en = SECTION_SEPARATOR.join(s.text for s in sections_en)
    tags = _merge_tags(source.categories, llm.classify(title_en, text_en, categories))
    if source.allow_narrowing:
        extent_id, reason = narrow_extent(tree, source.default_extent_id, text_en)
    else:
        extent_id, reason = source.default_extent_id, SOURCE_DEFAULT
    return EnrichedDocument(fetched=doc, title_en=title_en, sections_en=sections_en,
                            extent_id=extent_id, extent_reason=reason, categories=tags)
