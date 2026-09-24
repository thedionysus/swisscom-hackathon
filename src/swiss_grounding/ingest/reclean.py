"""Drop boilerplate chunks and any document left with none. No network, no model calls.

Deleting a document here is deliberate: "this was wrongly ingested, erase it including its
history." `chunk.document_id` has `on delete cascade`, but `document_change.document_id`,
`document_change.previous_document_id`, and the self-referencing `document.superseded_by`
do not -- and every crawled document gets a `document_change` row (`ingest/persist.py`), so
on the live corpus every document reclean empties has one. Adding `on delete cascade` to
those foreign keys in the schema was rejected -- that would silently erase audit history on
every future deletion path, not just this one deliberate one -- so `reclean_all` clears the
three FKs itself, inside the same transaction, with two different treatments:

- A `document_change` row is *deleted* only when its own `document_id` is a document being
  dropped: that row's entire subject is being erased, so its history goes with it. Likewise
  `superseded_by` -- always a full document's own column -- is nulled wherever it points at a
  dropped document.
- A `document_change` row whose `previous_document_id` points at a dropped document but whose
  `document_id` is a *surviving* document is not touched by the delete: reclean's licence is
  to erase the history of the documents it drops, not to punch holes in the history of
  documents it keeps. That row's dangling `previous_document_id` is nulled instead, the same
  way a dangling `superseded_by` is, and the row itself survives.

`document_change.chunks_added/chunks_removed/chunks_modified` are left alone. They are
`bigint[]` columns holding chunk ids, including ids of chunks this run deletes -- an array
cannot carry a foreign key, so nothing breaks when an id inside one stops existing, and
nothing reads them today. That silence is a decision, not an oversight: revisit only if
something starts reading those arrays back into live chunk ids.

`fetch_state` rows for recleaned URLs are left untouched on purpose. It was unsafe to clear
them while boilerplate was still ingested; now that `ingest/context.py` drops it at ingestion,
a re-fetch would end in a skipped document rather than re-inserting what this dropped, so the
reason has changed from unsafe to merely unnecessary. Clearing them would buy a re-crawl and a
model call per surviving chunk, and buy nothing else.

This command is the cleanup for chunks indexed before boilerplate was excluded at ingestion.
Once the `recontext` backfill has run and ingestion excludes boilerplate on the way in, it has
nothing left to do.
"""
from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import psycopg

from swiss_grounding.ingest.boilerplate import is_boilerplate

SELECT_CHUNKS = """
select c.id, c.document_id, c.heading_path, c.text_en, d.source_id
from chunk c join document d on d.id = c.document_id
"""
DELETE_CHUNKS = "delete from chunk where id = any(%s)"
DELETE_CHANGES_OF_DROPPED_DOCUMENTS = "delete from document_change where document_id = any(%s)"
CLEAR_PREVIOUS_DOCUMENT_ID = (
    "update document_change set previous_document_id = null where previous_document_id = any(%s)"
)
CLEAR_SUPERSEDED_BY = "update document set superseded_by = null where superseded_by = any(%s)"
DELETE_DOCUMENTS = "delete from document where id = any(%s)"


@dataclass(frozen=True)
class SourceReclean:
    """Chunks and documents dropped for one source."""

    source_id: str
    dropped_chunks: int
    dropped_documents: int


@dataclass(frozen=True)
class RecleanReport:
    """The full reclean result: how many chunks were examined, and the drops per source."""

    examined: int
    by_source: tuple[SourceReclean, ...]

    @property
    def dropped_chunks(self) -> int:
        return sum(s.dropped_chunks for s in self.by_source)

    @property
    def dropped_documents(self) -> int:
        return sum(s.dropped_documents for s in self.by_source)


def _summarise(
    boilerplate_rows: Sequence[Mapping[str, Any]], dropped_document_ids: Collection[int]
) -> tuple[SourceReclean, ...]:
    """Pure aggregation: one `SourceReclean` per source, sorted by `source_id`.

    `dropped_document_ids` are the (already-computed) ids of documents left with no chunks;
    a document is credited to whichever source owns the boilerplate rows sitting on it.
    """
    dropped_document_ids = set(dropped_document_ids)
    chunks_per_source: Counter[str] = Counter()
    dropped_documents_per_source: dict[str, set[int]] = {}
    for row in boilerplate_rows:
        source_id = row["source_id"]
        chunks_per_source[source_id] += 1
        if row["document_id"] in dropped_document_ids:
            dropped_documents_per_source.setdefault(source_id, set()).add(row["document_id"])

    return tuple(
        SourceReclean(
            source_id=source_id,
            dropped_chunks=dropped_chunks,
            dropped_documents=len(dropped_documents_per_source.get(source_id, set())),
        )
        for source_id, dropped_chunks in sorted(chunks_per_source.items())
    )


def delete_documents(conn: psycopg.Connection, document_ids: Sequence[int]) -> None:
    """Erase documents and the audit rows that point at them, per this module's two treatments.

    Public because `recontext` empties documents too -- a page the model judges furniture from
    top to bottom -- and the foreign keys that have to be cleared first are decided here, not
    there. Written twice they could be fixed once, and `coverage_rows` counts documents, so a
    document left behind with no chunks would keep reporting coverage it can no longer serve.
    """
    if not document_ids:
        return
    ids = list(document_ids)
    conn.execute(DELETE_CHANGES_OF_DROPPED_DOCUMENTS, (ids,))
    conn.execute(CLEAR_PREVIOUS_DOCUMENT_ID, (ids,))
    conn.execute(CLEAR_SUPERSEDED_BY, (ids,))
    conn.execute(DELETE_DOCUMENTS, (ids,))


def reclean_all(conn: psycopg.Connection, dry_run: bool = False) -> RecleanReport:
    """Delete every boilerplate chunk (`is_boilerplate`) and any document left with none.

    Heading-based rules only: boilerplate must be excluded at ingestion, not
    at ranking, because neither topic nor similarity can separate it from content.

    With `dry_run=True`, the report is computed exactly as normal but no statement that
    mutates the database runs -- irreversible, and against a predicate the module's own
    docstring calls provisional, so a caller can see the count before committing to it.
    """
    rows = conn.execute(SELECT_CHUNKS).fetchall()
    examined = len(rows)
    boilerplate_ids = {row["id"] for row in rows if is_boilerplate(row["heading_path"], row["text_en"])}
    if not boilerplate_ids:
        return RecleanReport(examined=examined, by_source=())

    boilerplate = [row for row in rows if row["id"] in boilerplate_ids]
    documents_with_a_surviving_chunk = {row["document_id"] for row in rows if row["id"] not in boilerplate_ids}
    touched_document_ids = sorted({row["document_id"] for row in boilerplate})
    empty_document_ids = [
        doc_id for doc_id in touched_document_ids if doc_id not in documents_with_a_surviving_chunk
    ]

    if not dry_run:
        conn.execute(DELETE_CHUNKS, ([row["id"] for row in boilerplate],))
        delete_documents(conn, empty_document_ids)

    return RecleanReport(examined=examined, by_source=_summarise(boilerplate, empty_document_ids))
