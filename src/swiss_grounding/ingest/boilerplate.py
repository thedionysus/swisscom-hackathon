"""Deterministic predicate for boilerplate chunks: page furniture, not content.

Heading-based rules only, per ADR 0005 (`docs/adr/0005-generated-context-steers-retrieval-and-is-never-cited.md`):
neither topic nor similarity can separate a navigation menu or an error page body from real
content, so it must be excluded at ingestion. A model-generated judgement (Task 5) supersedes
this heuristic once every chunk carries a generated description; until then, `text_en` is
accepted for a stable call signature but not yet consulted.

The two-argument signature is pinned by the plan's own unit tests below, not chosen with
Task 5 in mind: ADR 0005 has Task 5 judge boilerplate from a *generated description* of the
chunk, not from `text_en` itself, so this signature is probably not the one Task 5 wants.
Read the ADR before assuming `text_en` is a head start on that work.
"""

# Exact `heading_path` values known to hold page furniture rather than content. Every producer
# of Section.heading_path (html_sections.py, fetchers/fedlex.py, fetchers/api.py's _render)
# already strips its result, so heading_path is never padded and needs no normalizing here.
BOILERPLATE_HEADINGS: frozenset[str] = frozenset({
    "Navigation",
    "Error Page (404)",
})


def is_boilerplate(heading_path: str, text_en: str) -> bool:
    """True when a chunk is page furniture (navigation, an error page body), not content."""
    return heading_path in BOILERPLATE_HEADINGS
