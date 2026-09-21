"""Deterministic predicate for boilerplate chunks: page furniture, not content.

Heading-based rules only, per ADR 0005 (`docs/adr/0005-generated-context-steers-retrieval-and-is-never-cited.md`):
neither topic nor similarity can separate a navigation menu or an error page body from real
content, so it must be excluded at ingestion. A model-generated judgement (Task 5) supersedes
this heuristic once every chunk carries a generated description; until then, `text_en` is
accepted for a stable call signature but not yet consulted.
"""

# Exact `heading_path` values known to hold page furniture rather than content.
BOILERPLATE_HEADINGS: frozenset[str] = frozenset({
    "Navigation",
    "Error Page (404)",
})


def is_boilerplate(heading_path: str, text_en: str) -> bool:
    """True when a chunk is page furniture (navigation, an error page body), not content."""
    return heading_path.strip() in BOILERPLATE_HEADINGS
