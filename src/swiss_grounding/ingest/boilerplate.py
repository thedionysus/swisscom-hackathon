"""Deterministic predicate for boilerplate chunks: page furniture, not content.

Heading-based rules only, per ADR 0005 (`docs/adr/0005-generated-context-steers-retrieval-and-is-never-cited.md`):
neither topic nor similarity can separate a navigation menu or an error page body from real
content, so it must be excluded at ingestion.

The model's judgement (`ingest/context.py`) supersedes this predicate in *reach*, not in
authority. It sees every chunk and can call anything furniture; this predicate sees two exact
headings and is consulted first, because a chunk headed `Navigation` is furniture beyond
argument and a call spent confirming it is a call wasted -- 79 of the corpus's chunks carry
one of these two headings. Where the two could disagree, the model is never asked. That is
deliberate: the only disagreement possible is the model wanting to keep a navigation menu.

`text_en` is accepted and not consulted. It is kept because `reclean` passes it and because a
later rule may want it, not because these rules read it.
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
