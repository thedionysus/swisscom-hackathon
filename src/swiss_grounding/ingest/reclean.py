"""Drop boilerplate chunks and any document left with none. No network, no model calls."""
from dataclasses import dataclass

import psycopg

from swiss_grounding.ingest.boilerplate import is_boilerplate

SELECT_CHUNKS = """
select c.id, c.document_id, c.heading_path, c.text_en, d.source_id
from chunk c join document d on d.id = c.document_id
"""
DELETE_CHUNKS = "delete from chunk where id = any(%s)"
SELECT_SURVIVING_DOCUMENTS = "select distinct document_id from chunk where document_id = any(%s)"
DELETE_DOCUMENTS = "delete from document where id = any(%s)"


@dataclass(frozen=True)
class SourceReclean:
    """Chunks and documents dropped for one source."""

    source_id: str
    dropped_chunks: int
    dropped_documents: int


@dataclass(frozen=True)
class RecleanReport:
    """The full reclean result, broken down per source."""

    by_source: tuple[SourceReclean, ...]

    @property
    def dropped_chunks(self) -> int:
        return sum(s.dropped_chunks for s in self.by_source)

    @property
    def dropped_documents(self) -> int:
        return sum(s.dropped_documents for s in self.by_source)


def reclean_all(conn: psycopg.Connection) -> RecleanReport:
    """Delete every boilerplate chunk (`is_boilerplate`) and any document left with none.

    Heading-based rules only, per ADR 0005: boilerplate must be excluded at ingestion, not
    at ranking, because neither topic nor similarity can separate it from content.
    """
    rows = conn.execute(SELECT_CHUNKS).fetchall()
    boilerplate = [row for row in rows if is_boilerplate(row["heading_path"], row["text_en"])]
    if not boilerplate:
        return RecleanReport(by_source=())

    chunk_ids = [row["id"] for row in boilerplate]
    conn.execute(DELETE_CHUNKS, (chunk_ids,))

    touched_document_ids = sorted({row["document_id"] for row in boilerplate})
    surviving_document_ids = {
        row["document_id"]
        for row in conn.execute(SELECT_SURVIVING_DOCUMENTS, (touched_document_ids,)).fetchall()
    }
    empty_document_ids = [doc_id for doc_id in touched_document_ids if doc_id not in surviving_document_ids]
    if empty_document_ids:
        conn.execute(DELETE_DOCUMENTS, (empty_document_ids,))
    empty_document_id_set = set(empty_document_ids)

    chunks_dropped_by_source: dict[str, int] = {}
    documents_dropped_by_source: dict[str, set[int]] = {}
    for row in boilerplate:
        source_id = row["source_id"]
        chunks_dropped_by_source[source_id] = chunks_dropped_by_source.get(source_id, 0) + 1
        if row["document_id"] in empty_document_id_set:
            documents_dropped_by_source.setdefault(source_id, set()).add(row["document_id"])

    by_source = tuple(
        SourceReclean(
            source_id=source_id,
            dropped_chunks=dropped_chunks,
            dropped_documents=len(documents_dropped_by_source.get(source_id, ())),
        )
        for source_id, dropped_chunks in sorted(chunks_dropped_by_source.items())
    )
    return RecleanReport(by_source=by_source)
