import json
from collections.abc import Iterable
from dataclasses import dataclass

import psycopg

from swiss_grounding.ingest.fetch_state import forget_known, save_known, touch_known
from swiss_grounding.ingest.hashing import content_hash, text_hash
from swiss_grounding.ingest.models import ChunkDraft, EnrichedDocument, KnownUrl
from swiss_grounding.retrieval.embedder import Embedder

ADDED = "added"
MODIFIED = "modified"
WITHDRAWN = "withdrawn"
SKIPPED = "skipped"


@dataclass(frozen=True)
class PersistOutcome:
    document_id: int | None
    change_type: str | None      # "added" | "modified" | "skipped" | None (unchanged)


def _current(conn: psycopg.Connection, url: str) -> dict | None:
    return conn.execute(
        "select id, version, content_hash from document where url = %s and status = 'current'", (url,)
    ).fetchone()


def _insert_document(conn: psycopg.Connection, doc: EnrichedDocument, chash: str, version: int) -> int:
    f = doc.fetched
    row = conn.execute(
        """
        insert into document (source_id, url, identifier, title_original, title_en, language, extent_id,
                              extent_reason, authority, categories, valid_from, valid_to, in_force,
                              event_date, published_at, content_hash, version)
        select %s, %s, %s, %s, %s, %s, %s, %s, s.authority, %s::jsonb, %s, %s, %s, %s, %s, %s, %s
        from source s where s.id = %s
        returning id
        """,
        (f.source_id, f.url, f.identifier, f.title, doc.title_en, f.language, doc.extent_id,
         doc.extent_reason, json.dumps([{"id": t.id, "confidence": t.confidence} for t in doc.categories]),
         f.valid_from, f.valid_to, f.in_force, f.event_date, f.published_at, chash, version, f.source_id),
    ).fetchone()
    if row is None:
        raise ValueError(f"unknown source id {f.source_id!r}")
    return row["id"]


def _insert_chunks(conn: psycopg.Connection, document_id: int, doc: EnrichedDocument,
                   chunks: tuple[ChunkDraft, ...], embedder: Embedder) -> dict[str, int]:
    """Insert chunks; returns chunk_hash -> chunk id."""
    vectors = embedder.embed([c.text_en for c in chunks]) if chunks else []
    authority = conn.execute("select authority from document where id = %s", (document_id,)).fetchone()["authority"]
    ids: dict[str, int] = {}
    for chunk, vector in zip(chunks, vectors, strict=True):
        chash = text_hash(chunk.text_en)
        row = conn.execute(
            """
            insert into chunk (document_id, ordinal, text_original, text_en, heading_path, anchor, embedding,
                               chunk_hash, extent_id, authority, categories)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id
            """,
            (document_id, chunk.ordinal, chunk.text_original, chunk.text_en, chunk.heading_path, chunk.anchor,
             vector, chash, doc.extent_id, authority, [t.id for t in doc.categories]),
        ).fetchone()
        ids[chash] = row["id"]
    return ids


def _diff(conn: psycopg.Connection, previous_id: int, new_ids: dict[str, int]) -> tuple[list[int], list[int], list[int]]:
    old = {r["chunk_hash"]: r["id"] for r in conn.execute(
        "select id, chunk_hash from chunk where document_id = %s", (previous_id,)).fetchall()}
    added = [cid for h, cid in new_ids.items() if h not in old]
    removed = [cid for h, cid in old.items() if h not in new_ids]
    # a "modified" chunk is one whose ordinal position exists in both versions but whose hash changed
    modified = added[: min(len(added), len(removed))]
    added = added[len(modified):]
    removed = removed[len(modified):]
    return added, removed, modified


def _log_change(conn: psycopg.Connection, run_id: str, document_id: int | None, previous_id: int | None,
                change_type: str, added: Iterable[int] = (), removed: Iterable[int] = (),
                modified: Iterable[int] = ()) -> None:
    conn.execute(
        """
        insert into document_change (run_id, document_id, previous_document_id, change_type,
                                     chunks_added, chunks_removed, chunks_modified)
        values (%s, %s, %s, %s, %s, %s, %s)
        """,
        (run_id, document_id, previous_id, change_type, list(added), list(removed), list(modified)),
    )


def _skip(conn: psycopg.Connection, doc: EnrichedDocument, chash: str, current: dict | None) -> PersistOutcome:
    """Record a document that holds nothing to index, without storing it.

    A document with no chunks is invisible to search, so writing one and calling it added would
    report a success the index cannot show. It is not a failure either: no retry puts chunks into a
    page that has none, which is why this is an outcome rather than a raised error.

    A URL seen for the first time has its content remembered, so the next run treats it as unchanged
    instead of fetching, translating and classifying a page it will discard again. A URL whose
    earlier version is still stored is deliberately not remembered: it held evidence and holds none
    now, so the stored version stays served and the next run looks again rather than accepting the
    loss on the strength of one empty read.
    """
    f = doc.fetched
    if current is None:
        save_known(conn, f.source_id, f.url,
                   KnownUrl(etag=f.etag, last_modified=f.last_modified, content_hash=chash))
    return PersistOutcome(document_id=None, change_type=SKIPPED)


def persist_document(conn: psycopg.Connection, doc: EnrichedDocument, chunks: tuple[ChunkDraft, ...],
                     embedder: Embedder, run_id: str) -> PersistOutcome:
    """Insert a new version when content changed; supersede the previous; log a chunk-level diff.

    A document that chunked to nothing is skipped instead: see `_skip`.
    """
    f = doc.fetched
    chash = content_hash(f)
    current = _current(conn, f.url)
    if current and current["content_hash"] == chash:
        touch_unchanged(conn, f.url)
        return PersistOutcome(document_id=current["id"], change_type=None)
    if not chunks:
        return _skip(conn, doc, chash, current)
    version = (current["version"] + 1) if current else 1
    document_id = _insert_document(conn, doc, chash, version)
    new_ids = _insert_chunks(conn, document_id, doc, chunks, embedder)
    save_known(conn, f.source_id, f.url, KnownUrl(etag=f.etag, last_modified=f.last_modified, content_hash=chash))
    if current is None:
        _log_change(conn, run_id, document_id, None, ADDED, added=new_ids.values())
        return PersistOutcome(document_id=document_id, change_type=ADDED)
    conn.execute(
        "update document set status = 'superseded', superseded_by = %s, valid_to = coalesce(valid_to, %s) where id = %s",
        (document_id, f.valid_from, current["id"]),
    )
    conn.execute("update chunk set document_status = 'superseded' where document_id = %s", (current["id"],))
    added, removed, modified = _diff(conn, current["id"], new_ids)
    _log_change(conn, run_id, document_id, current["id"], MODIFIED, added, removed, modified)
    return PersistOutcome(document_id=document_id, change_type=MODIFIED)


def touch_unchanged(conn: psycopg.Connection, url: str) -> None:
    conn.execute("update document set retrieved_at = now() where url = %s and status = 'current'", (url,))
    touch_known(conn, url)


def mark_withdrawn(conn: psycopg.Connection, url: str, run_id: str) -> bool:
    """Mark the current version withdrawn; keep the row so old citations resolve. Returns False if none."""
    current = _current(conn, url)
    if current is None:
        return False
    conn.execute("update document set status = 'withdrawn' where id = %s", (current["id"],))
    conn.execute("update chunk set document_status = 'withdrawn' where document_id = %s", (current["id"],))
    forget_known(conn, url)
    _log_change(conn, run_id, current["id"], None, WITHDRAWN)
    return True
