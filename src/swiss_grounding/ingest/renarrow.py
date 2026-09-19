"""Re-run narrowing over stored documents using their stored English text. No API calls."""
from dataclasses import dataclass

import psycopg

from swiss_grounding.ingest.narrowing import SOURCE_DEFAULT, narrow_extent
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.repository import load_sources

SELECT = """
select d.id, d.source_id, d.title_en, d.extent_id, d.extent_reason,
       array_agg(c.heading_path order by c.ordinal) as headings,
       string_agg(c.text_en, ' ' order by c.ordinal) as text_en
from document d join chunk c on c.document_id = d.id
where d.status = 'current' group by d.id
"""
UPDATE_DOC = "update document set extent_id = %s, extent_reason = %s where id = %s"
UPDATE_CHUNKS = "update chunk set extent_id = %s where document_id = %s"


@dataclass(frozen=True)
class RenarrowReport:
    examined: int
    moved: int
    skipped: int = 0
    relabelled: int = 0   # extent unchanged, reason text refreshed


def renarrow_all(conn: psycopg.Connection, tree: LocationTree) -> RenarrowReport:
    """Re-narrow every current document from its stored title, headings, and English text.

    A document whose source has since been removed from the registry is skipped, not fatal.
    """
    sources = {s.id: s for s in load_sources(conn)}
    examined = moved = skipped = relabelled = 0
    for row in conn.execute(SELECT).fetchall():
        examined += 1
        source = sources.get(row["source_id"])
        if source is None:
            skipped += 1
            continue
        if not source.allow_narrowing:
            target, reason = source.default_extent_id, SOURCE_DEFAULT
        else:
            headings = tuple(h for h in row["headings"] if h)
            target, reason = narrow_extent(tree, source.default_extent_id, row["title_en"], headings,
                                           row["text_en"] or "")
        if target != row["extent_id"]:
            conn.execute(UPDATE_DOC, (target, reason, row["id"]))
            conn.execute(UPDATE_CHUNKS, (target, row["id"]))
            moved += 1
        elif reason != row["extent_reason"]:
            conn.execute(UPDATE_DOC, (target, reason, row["id"]))
            relabelled += 1
    return RenarrowReport(examined=examined, moved=moved, skipped=skipped, relabelled=relabelled)
