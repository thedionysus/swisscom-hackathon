"""Write parsed documents and their chunks: versions, supersede, fetch state, quarantine.

Rules:
1. Same URL, same content hash: touch `last_seen_at`; a status change (scheduled -> current) is applied
   in place. Outcome `unchanged`.
2. Same URL, different hash: the old row is superseded by a new row. Outcome `modified`.
3. A new dated (`valid_from` set) `current` version retires the `current` and `scheduled` rows of the
   same translation group, language and source that start no later than it. Undated documents
   (HTML, PDF) are versioned by URL only (amendment A1). Outcome `added`.
   A URL already owned by another source is left alone: outcome `duplicate` (first owner wins).
4. `fetched_at` is when this content was fetched; `last_seen_at` when it was last confirmed.
5. Chunks carry document status, extent, authority and, for Fedlex, the SR prior topics.
"""
import hashlib
import json
import re
from datetime import date, datetime

import psycopg

from swiss_grounding.corpus.chunker import chunk_document
from swiss_grounding.corpus.models import (
    ChunkDraft,
    KnownState,
    ParsedDocument,
    SourceSpec,
    content_hash,
)
from swiss_grounding.corpus.topics import sr_prior

ARTICLE_NUMBER = re.compile(r"^art_(\d+)")


def group_id(work_key: str) -> str:
    return "g_" + hashlib.sha1(work_key.encode()).hexdigest()[:16]


def upsert_source(conn: psycopg.Connection, spec: SourceSpec) -> None:
    conn.execute(
        "insert into corpus.source (id, name, publisher, authority, level, extent_id, connector, tier, languages, config) "
        "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict (id) do update set name=excluded.name, "
        "publisher=excluded.publisher, authority=excluded.authority, level=excluded.level, "
        "extent_id=excluded.extent_id, connector=excluded.connector, tier=excluded.tier, "
        "languages=excluded.languages, config=excluded.config",
        (spec.id, spec.name, spec.publisher, spec.authority, spec.level, spec.extent_id, spec.connector,
         spec.tier, list(spec.languages), json.dumps(spec.config)))


def known_state(conn: psycopg.Connection, source_id: str) -> dict[str, KnownState]:
    rows = conn.execute("select url, etag, last_modified, content_hash from corpus.fetch_state where source_id = %s",
                        (source_id,)).fetchall()
    return {r["url"]: KnownState(r["etag"], r["last_modified"], r["content_hash"]) for r in rows}


def _prior_topics(doc: ParsedDocument, draft: ChunkDraft) -> list[str]:
    if not (doc.identifier and doc.identifier.startswith("SR ")):
        return []
    match = ARTICLE_NUMBER.match(draft.align_key)
    return list(sr_prior(doc.identifier[3:], int(match.group(1)) if match else None))


def _chunk_hash(draft: ChunkDraft) -> str:
    """Text for a native chunk; for an OCR page the image digest, so a new scan is described again."""
    return hashlib.sha256((draft.text or draft.ocr_digest or draft.ocr_image or "").encode()).hexdigest()


def _set_status(conn: psycopg.Connection, doc_ids: list[int], status: str) -> None:
    if doc_ids:
        conn.execute("update corpus.document set status = %s where id = any(%s)", (status, doc_ids))
        conn.execute("update corpus.chunk set status = %s where document_id = any(%s) and status <> 'boilerplate'",
                     (status, doc_ids))


def _supersede_others(conn, gid: str, language: str, source_id: str, keep_id: int, keep_from: date) -> None:
    """Retire the current and scheduled peers that `keep_id` replaces: those in force no later than it.

    A peer with a later `valid_from` is newer than `keep_id` and stays (a stale version never retires it).
    """
    rows = conn.execute(
        "select id from corpus.document where translation_group_id = %s and language = %s and source_id = %s "
        "and status in ('current','scheduled') and id <> %s and (valid_from is null or valid_from <= %s)",
        (gid, language, source_id, keep_id, keep_from)).fetchall()
    ids = [r["id"] for r in rows]
    if ids:
        conn.execute("update corpus.document set superseded_by = %s, valid_to = coalesce(valid_to, %s) "
                     "where id = any(%s)", (keep_id, keep_from, ids))
        _set_status(conn, ids, "superseded")


def _retires_group_peers(doc: ParsedDocument) -> bool:
    """Rule 3 applies only to dated consolidations (amendment A1)."""
    return doc.status == "current" and doc.valid_from is not None


def _insert(conn, doc: ParsedDocument, spec: SourceSpec, gid: str, digest: str, now: datetime) -> int:
    doc_id = conn.execute(
        "insert into corpus.document (source_id, url, language, translation_group_id, title, identifier, publisher, "
        "authority, extent_id, is_authentic, valid_from, valid_to, status, published_at, modified_at, fetched_at, "
        "last_seen_at, content_hash, extraction, retrieved_via, artifact_path) values "
        "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) returning id",
        (doc.source_id, doc.url, doc.language, gid, doc.title, doc.identifier, spec.publisher, spec.authority,
         spec.extent_id, doc.is_authentic, doc.valid_from, doc.valid_to, doc.status, doc.published_at,
         doc.modified_at, now, now, digest, doc.extraction, doc.retrieved_via or spec.retrieved_via,
         doc.artifact_path)).fetchone()["id"]
    drafts = chunk_document(doc)
    with conn.cursor() as cur:
        cur.executemany(
            "insert into corpus.chunk (document_id, language, translation_group_id, align_key, ordinal, breadcrumb, "
            "anchor, text, topics, extent_id, authority, status, chunk_hash, needs_ocr, ocr_image) values "
            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            [(doc_id, doc.language, gid, d.align_key, d.ordinal, list(d.breadcrumb), d.anchor, d.text,
              _prior_topics(doc, d), spec.extent_id, spec.authority, doc.status, _chunk_hash(d),
              d.needs_ocr, d.ocr_image)
             for d in drafts])
    _reuse_descriptions(conn, doc_id)
    return doc_id


def _reuse_descriptions(conn, doc_id: int) -> None:
    """Copy description, topics and a boilerplate verdict from an earlier version's identical chunk.

    RAG review E3: a chunk whose text did not change between versions keeps what was already paid for.
    Identity is (translation group, language, align_key, chunk_hash), so a changed text is described again.
    """
    conn.execute(
        "update corpus.chunk n set description = m.description, topics = m.topics, "
        "status = case when m.status = 'boilerplate' then 'boilerplate' else n.status end "
        "from (select distinct on (c.id) c.id as chunk_id, o.description, o.topics, o.status "
        "      from corpus.chunk c join corpus.chunk o on o.translation_group_id = c.translation_group_id "
        "       and o.language = c.language and o.align_key = c.align_key and o.chunk_hash = c.chunk_hash "
        "       and o.document_id <> c.document_id and o.description <> '' "
        "      where c.document_id = %s order by c.id, o.id desc) m "
        "where n.id = m.chunk_id and n.document_id = %s",
        (doc_id, doc_id))


def _upsert_fetch_state(conn, doc: ParsedDocument, digest: str, now: datetime) -> None:
    conn.execute(
        "insert into corpus.fetch_state (url, source_id, etag, last_modified, content_hash, last_seen_at) "
        "values (%s,%s,%s,%s,%s,%s) on conflict (url) do update set source_id=excluded.source_id, "
        "etag=excluded.etag, last_modified=excluded.last_modified, content_hash=excluded.content_hash, "
        "last_seen_at=excluded.last_seen_at",
        (doc.url, doc.source_id, doc.etag, doc.last_modified, digest, now))


def _reissue_end(live_from: date | None, doc: ParsedDocument, now: datetime) -> date | None:
    """When a row replaced at its own URL stops applying; never a zero-length or negative interval.

    A re-issue with a later `valid_from` ends the old row on that date; an undated or same-date
    re-issue ends it today. A row that would end on or before its own start was never in force: None.
    """
    end = doc.valid_from if (doc.valid_from and live_from and doc.valid_from > live_from) else now.date()
    return None if live_from is not None and end <= live_from else end


def _clear_quarantine(conn, source_id: str, url: str) -> None:
    conn.execute("delete from corpus.quarantine where source_id = %s and url = %s and stage in ('fetch','persist')",
                 (source_id, url))


def persist_document(conn: psycopg.Connection, doc: ParsedDocument, spec: SourceSpec, now: datetime) -> str:
    """Write one parsed document. Returns 'added', 'modified', 'unchanged' or 'duplicate'.

    'duplicate' means another source already owns the URL; first owner wins and nothing is touched.
    """
    live = conn.execute("select id, content_hash, status, source_id, valid_from from corpus.document "
                        "where url = %s and status in ('current','scheduled')", (doc.url,)).fetchone()
    if live and live["source_id"] != doc.source_id:
        return "duplicate"
    gid = group_id(doc.work_key)
    conn.execute("insert into corpus.translation_group (id, work_key) values (%s, %s) on conflict (id) do nothing",
                 (gid, doc.work_key))
    digest = content_hash(doc)
    if live and live["content_hash"] == digest:
        conn.execute("update corpus.document set last_seen_at = %s where id = %s", (now, live["id"]))
        if live["status"] != doc.status:
            _set_status(conn, [live["id"]], doc.status)
            if _retires_group_peers(doc):
                _supersede_others(conn, gid, doc.language, doc.source_id, live["id"], doc.valid_from)
        outcome = "unchanged"
    else:
        if live:
            _set_status(conn, [live["id"]], "superseded")
        doc_id = _insert(conn, doc, spec, gid, digest, now)
        if live:
            conn.execute("update corpus.document set superseded_by = %s, valid_to = coalesce(valid_to, %s) "
                         "where id = %s", (doc_id, _reissue_end(live["valid_from"], doc, now), live["id"]))
        if _retires_group_peers(doc):
            _supersede_others(conn, gid, doc.language, doc.source_id, doc_id, doc.valid_from)
        outcome = "modified" if live else "added"
    _upsert_fetch_state(conn, doc, digest, now)
    _clear_quarantine(conn, doc.source_id, doc.url)
    return outcome


def promote_due(conn: psycopg.Connection, today: date) -> int:
    """Make every scheduled version whose `valid_from` has arrived current (amendment A5).

    Each promoted version retires the older current row of its group/language/source with
    `valid_to = valid_from`. A scheduled version that a current peer with the same or a later
    `valid_from` already overtook is superseded by that peer instead. Boilerplate chunks stay
    boilerplate. Returns the number promoted.
    """
    due = conn.execute(
        "select id, translation_group_id, language, source_id, valid_from from corpus.document "
        "where status = 'scheduled' and valid_from <= %s order by valid_from, id", (today,)).fetchall()
    promoted = 0
    for row in due:
        newer = conn.execute(
            "select id from corpus.document where translation_group_id = %s and language = %s and source_id = %s "
            "and status = 'current' and valid_from >= %s order by valid_from desc, id desc limit 1",
            (row["translation_group_id"], row["language"], row["source_id"], row["valid_from"])).fetchone()
        if newer:
            conn.execute("update corpus.document set superseded_by = %s where id = %s", (newer["id"], row["id"]))
            _set_status(conn, [row["id"]], "superseded")
            continue
        _set_status(conn, [row["id"]], "current")
        _supersede_others(conn, row["translation_group_id"], row["language"], row["source_id"], row["id"],
                          row["valid_from"])
        promoted += 1
    return promoted


def touch_unchanged(conn: psycopg.Connection, url: str, now: datetime) -> None:
    conn.execute("update corpus.document set last_seen_at = %s where url = %s and status in ('current','scheduled')",
                 (now, url))
    conn.execute("update corpus.fetch_state set last_seen_at = %s where url = %s", (now, url))


def withdraw(conn: psycopg.Connection, url: str) -> None:
    ids = [r["id"] for r in conn.execute(
        "select id from corpus.document where url = %s and status in ('current','scheduled')", (url,)).fetchall()]
    _set_status(conn, ids, "withdrawn")
    conn.execute("delete from corpus.fetch_state where url = %s", (url,))


def quarantine(conn: psycopg.Connection, source_id: str, url: str, stage: str, reason: str) -> None:
    conn.execute(
        "insert into corpus.quarantine (source_id, url, stage, reason) values (%s,%s,%s,%s) "
        "on conflict (source_id, url, stage) do update set attempts = corpus.quarantine.attempts + 1, "
        "reason = excluded.reason, last_at = now()", (source_id, url, stage, reason[:2000]))
