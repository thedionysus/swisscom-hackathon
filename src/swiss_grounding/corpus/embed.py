"""Embed stage: the text each chunk is embedded as, the OpenAI Batch and in-process paths, and the HNSW build.

The embedded text is breadcrumb + description + text; its SHA-256 (`text_hash`) is stored with the vector, so a
chunk whose description or text changes is re-embedded and an identical chunk of a new version reuses its vector.
"""
import hashlib
import json
import logging
from collections.abc import Sequence

import numpy as np
import psycopg
import psycopg.sql
from pgvector import HalfVector, SparseVector

from swiss_grounding.corpus.budget import PRICES, cost_usd, estimate_tokens, record_spend
from swiss_grounding.corpus.providers import BGE_M3_VOCAB, IndexSpec
from swiss_grounding.corpus.runner import EMBEDDINGS_ENDPOINT
from swiss_grounding.db.connection import connect

log = logging.getLogger(__name__)
MAX_EMBED_CHARS = 12_000
LANGS = ("de", "fr", "it", "en", "rm")
WRITE_BLOCK = 1000          # vectors written and committed together on the batch path
EMBED_KIND = "embed"
ELIGIBLE = "c.status in ('current','scheduled') and c.text <> ''"

# The SHA-256 of `embedding_text` computed in Postgres, over `corpus.chunk c`. Must match `_hash(embedding_text(...))`
# (tested): parts joined by newline with empty parts skipped, then cut to MAX_EMBED_CHARS characters.
TEXT_HASH_SQL = (
    "encode(sha256(convert_to(left(concat_ws(E'\\n', nullif(array_to_string(c.breadcrumb, ' > '), ''), "
    f"nullif(c.description, ''), nullif(c.text, '')), {MAX_EMBED_CHARS}), 'UTF8')), 'hex')"
)


def embedding_text(breadcrumb, description: str, text: str) -> str:
    parts = [" > ".join(breadcrumb or []), description or "", text or ""]
    return "\n".join(p for p in parts if p)[:MAX_EMBED_CHARS]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def pending_for_index(conn: psycopg.Connection, index: IndexSpec, require_description: bool,
                      limit: int | None) -> list[dict]:
    """Eligible chunks whose stored vector is missing or was made from a different text.

    The hash comparison runs in SQL so `limit` counts only chunks that actually need embedding.
    """
    rows = conn.execute(
        f"select c.id, c.language, c.breadcrumb, c.description, c.text "
        f"from corpus.chunk c left join {index.table} e on e.chunk_id = c.id and e.language = c.language "
        f"where {ELIGIBLE} and (not %s or c.description <> '') "
        f"and e.text_hash is distinct from {TEXT_HASH_SQL} order by c.id limit %s",
        (require_description, limit)).fetchall()
    out = []
    for r in rows:
        text = embedding_text(r["breadcrumb"], r["description"], r["text"])
        out.append({"id": r["id"], "language": r["language"], "text": text, "hash": _hash(text)})
    return out


def _has_sparse(index: IndexSpec) -> bool:
    return index.name == "bge-m3"


def _write(conn: psycopg.Connection, index: IndexSpec, rows: Sequence[tuple]) -> None:
    """rows: (chunk_id, language, text_hash, dense[, sparse dict or None])."""
    wrap = HalfVector if index.opclass.startswith("halfvec") else (lambda v: v)
    with_sparse = _has_sparse(index)
    cols = "chunk_id, language, text_hash, embedding" + (", sparse" if with_sparse else "")
    marks = "%s,%s,%s,%s" + (",%s" if with_sparse else "")
    update = "text_hash = excluded.text_hash, embedding = excluded.embedding" + (
        ", sparse = excluded.sparse" if with_sparse else "")
    values = []
    for row in rows:
        cid, lang, digest, vec = row[:4]
        item = [cid, lang, digest, wrap(np.asarray(vec, dtype=np.float32))]
        if with_sparse:
            sparse = row[4] if len(row) > 4 else None
            item.append(SparseVector(sparse, BGE_M3_VOCAB) if sparse else None)
        values.append(tuple(item))
    with conn.cursor() as cur:
        cur.executemany(f"insert into {index.table} ({cols}) values ({marks}) "
                        f"on conflict (chunk_id, language) do update set {update}", values)


def reuse_embeddings(conn: psycopg.Connection, index: IndexSpec, require_description: bool = True) -> int:
    """Copy stored vectors onto pending chunks whose embedded text is identical (RAG review E3, amendment A7).

    One set-based statement: for each eligible chunk without a vector for its current text, take any one stored
    vector with the same (text_hash, language) — an index lookup — and upsert it. Call it before building the
    pending list on every path (local, sync OpenAI, Batch) so an unchanged chunk of a new version is never paid for
    twice. Returns the number of vectors copied; the caller commits.
    """
    sparse = _has_sparse(index)
    extra_cols, extra_src = (", sparse", ", src.sparse") if sparse else ("", "")
    extra_update = ", sparse = excluded.sparse" if sparse else ""
    cur = conn.execute(
        f"with wanted as ("
        f"  select c.id, c.language, {TEXT_HASH_SQL} as h from corpus.chunk c "
        f"  where {ELIGIBLE} and (not %s or c.description <> '')), "
        f"pending as ("
        f"  select w.id, w.language, w.h from wanted w left join {index.table} own "
        f"    on own.chunk_id = w.id and own.language = w.language "
        f"  where own.text_hash is distinct from w.h) "
        f"insert into {index.table} (chunk_id, language, text_hash, embedding{extra_cols}) "
        f"select p.id, p.language, src.text_hash, src.embedding{extra_src} from pending p "
        f"cross join lateral (select e.text_hash, e.embedding{', e.sparse' if sparse else ''} from {index.table} e "
        f"  where e.text_hash = p.h and e.language = p.language limit 1) src "
        f"on conflict (chunk_id, language) do update set text_hash = excluded.text_hash, "
        f"embedding = excluded.embedding{extra_update}",
        (require_description,))
    return max(cur.rowcount, 0)


def _record_sync_spend(conn: psycopg.Connection, provider) -> None:
    """A9: a paid in-process provider (OpenAIEmbeddings) exposes `model` and `last_usage`; bill it at sync price."""
    model = getattr(provider, "model", None)
    tokens = getattr(provider, "last_usage", None)
    if model not in PRICES or not tokens:
        return
    record_spend(conn, kind=EMBED_KIND, model=model, usd=cost_usd(model, tokens, 0, batch=False),
                 input_tokens=tokens, output_tokens=0, estimated=False)


def token_groups(pending: Sequence[dict], max_items: int, max_tokens: int | None = None) -> list[list[dict]]:
    """Consecutive groups of at most `max_items` texts and, when given, `max_tokens` estimated tokens.
    A single text over `max_tokens` is sent on its own (the provider truncates or rejects it)."""
    groups: list[list[dict]] = []
    current: list[dict] = []
    tokens = 0
    for item in pending:
        cost = estimate_tokens(item["text"])
        if current and (len(current) >= max_items or (max_tokens is not None and tokens + cost > max_tokens)):
            groups.append(current)
            current, tokens = [], 0
        current.append(item)
        tokens += cost
    if current:
        groups.append(current)
    return groups


def embed_local(database_url: str, index: IndexSpec, provider, batch_size: int = 256,
                require_description: bool = True, max_tokens_per_request: int | None = None) -> int:
    """Embed pending chunks with an in-process provider, committing every batch (resumable).

    Vectors of unchanged chunks are copied first; a provider with `embed_with_sparse` also fills `sparse`; a paid
    provider's spend is recorded with each batch. A request holds at most `batch_size` texts and, when
    `max_tokens_per_request` is given, that many estimated tokens. Returns the number of vectors newly embedded.
    """
    written = 0
    with connect(database_url) as conn:
        log.info("%s: reused %d vector(s) from earlier versions", index.name,
                 reuse_embeddings(conn, index, require_description))
        conn.commit()
        pending = pending_for_index(conn, index, require_description, None)
        for part in token_groups(pending, batch_size, max_tokens_per_request):
            texts = [p["text"] for p in part]
            if hasattr(provider, "embed_with_sparse"):
                pairs = provider.embed_with_sparse(texts)
            else:
                pairs = [(v, None) for v in provider.embed(texts)]
            _write(conn, index, [(p["id"], p["language"], p["hash"], dense, sparse)
                                 for p, (dense, sparse) in zip(part, pairs, strict=True)])
            _record_sync_spend(conn, provider)
            conn.commit()
            written += len(part)
            log.info("%s: %d / %d embedded", index.name, written, len(pending))
    return written


def estimate_embeddings(pending: Sequence[dict], model: str, batch: bool = True) -> float:
    return cost_usd(model, sum(estimate_tokens(p["text"]) for p in pending), 0, batch=batch)


def _custom_id(p: dict) -> str:
    return f"{p['language']}|{p['id']}|{p['hash']}"


def _current_hashes(conn: psycopg.Connection, keys: Sequence[tuple[int, str]]) -> dict[tuple[int, str], str]:
    rows = conn.execute(
        f"select c.id, c.language, {TEXT_HASH_SQL} as h from corpus.chunk c "
        f"join unnest(%s::bigint[], %s::text[]) as k(id, lang) on c.id = k.id and c.language = k.lang",
        ([k[0] for k in keys], [k[1] for k in keys])).fetchall()
    return {(r["id"], r["language"]): r["h"] for r in rows}


def _flush(conn: psycopg.Connection, index: IndexSpec, rows: list[tuple], tokens: int, report: dict) -> None:
    """Write the rows whose chunk still exists with the same embedded text, record the block's spend, commit."""
    current = _current_hashes(conn, [(cid, lang) for cid, lang, _, _ in rows])
    fresh = [row for row in rows if current.get((row[0], row[1])) == row[2]]
    if fresh:
        _write(conn, index, fresh)
    if tokens:
        record_spend(conn, kind=EMBED_KIND, model=index.model, usd=cost_usd(index.model, tokens, 0),
                     input_tokens=tokens, output_tokens=0, estimated=False)
    conn.commit()
    report["written"] += len(fresh)
    report["stale"] += len(rows) - len(fresh)


def _parse_line(raw: str) -> tuple[str, list[float] | None, int, str | None]:
    """(custom_id, embedding or None, prompt tokens, error message or None) of one result line."""
    record = json.loads(raw)
    custom_id = record.get("custom_id", "?")
    response = record.get("response") or {}
    body = response.get("body") or {}
    if response.get("status_code") != 200:
        error = (record.get("error") or body.get("error") or {}).get("message") or json.dumps(response)[:300]
        return custom_id, None, 0, error
    try:
        return custom_id, body["data"][0]["embedding"], body.get("usage", {}).get("prompt_tokens", 0), None
    except (KeyError, IndexError, TypeError) as exc:
        return custom_id, None, body.get("usage", {}).get("prompt_tokens", 0), f"malformed body: {exc!r}"


def _ingest_batch(database_url: str, index: IndexSpec, batch_runner, batch_id: str,
                  expected: set[str] | None, report: dict) -> None:
    """Fetch one batch, write its vectors in committed blocks of WRITE_BLOCK, then mark it done (after the commit)."""
    seen: set[str] = set()
    with connect(database_url) as conn:
        rows, tokens = [], 0
        for raw in batch_runner.fetch(batch_id):
            custom_id, vector, used, error = _parse_line(raw)
            seen.add(custom_id)
            tokens += used
            if error is not None:
                log.warning("embed batch %s: %s failed: %s", batch_id, custom_id, error)
                report["failed"] += 1
                continue
            lang, cid, digest = custom_id.split("|")
            rows.append((int(cid), lang, digest, vector))
            if len(rows) >= WRITE_BLOCK:
                _flush(conn, index, rows, tokens, report)
                rows, tokens = [], 0
        if rows or tokens:
            _flush(conn, index, rows, tokens, report)
    missing = (expected or set()) - seen
    if missing:
        log.warning("embed batch %s: %d request(s) returned no result", batch_id, len(missing))
        report["failed"] += len(missing)
    batch_runner.done(batch_id)


def _new_report() -> dict[str, int]:
    return {"written": 0, "failed": 0, "stale": 0}


def embed_openai_batch(database_url: str, index: IndexSpec, batch_runner, pending: Sequence[dict],
                       estimated_usd: float | None = None) -> dict[str, int]:
    """Embed through the Batch API (half price), one file at a time. custom_id = '<lang>|<chunk_id>|<hash>'.

    Call `reuse_embeddings` before building `pending`. One input per line, so the runner's max_per_file (50,000)
    matches OpenAI's cap on embedding inputs per batch. Returns {"written", "failed", "stale"}: failed lines are
    logged and stay pending for the next run; stale results (chunk changed or deleted since submission) are skipped.
    """
    lines = [{"custom_id": _custom_id(p), "method": "POST", "url": EMBEDDINGS_ENDPOINT,
              "body": {"model": index.model, "input": p["text"]}} for p in pending]
    estimate = estimate_embeddings(pending, index.model) if estimated_usd is None else estimated_usd
    report = _new_report()
    for batch_id, group in batch_runner.submit_sequentially(lines, EMBED_KIND, EMBEDDINGS_ENDPOINT, estimate):
        _ingest_batch(database_url, index, batch_runner, batch_id, {line["custom_id"] for line in group}, report)
        log.info("%s: batch %s ingested, %s", index.name, batch_id, report)
    return report


def resume_embed_batches(database_url: str, index: IndexSpec, batch_runner,
                         batch_ids: Sequence[str]) -> dict[str, int]:
    """Ingest embed batches submitted by an earlier, interrupted run through the same writer (amendment A3)."""
    report = _new_report()
    for batch_id in batch_ids:
        _ingest_batch(database_url, index, batch_runner, batch_id, None, report)
    return report


def build_vector_indexes(database_url: str, index: IndexSpec, parallel_workers: int = 0,
                         maintenance_work_mem: str = "1GB") -> None:
    """HNSW per language partition. Build after bulk loading: inserting into a live HNSW index is far slower.

    `parallel_workers` > 0 speeds the build but needs shared memory: in Docker give the db service a large
    `shm_size`, else Postgres fails with "could not resize shared memory segment". 0 builds serially.
    """
    if parallel_workers < 0:
        raise ValueError("parallel_workers must be >= 0")
    table = index.table.split(".")[1]
    with connect(database_url) as conn:
        conn.execute(psycopg.sql.SQL("set maintenance_work_mem = {}").format(psycopg.sql.Literal(maintenance_work_mem)))
        conn.execute(psycopg.sql.SQL("set max_parallel_maintenance_workers = {}").format(
            psycopg.sql.Literal(parallel_workers)))
        for lang in LANGS:
            conn.execute(f"create index if not exists {table}_{lang}_hnsw on corpus.{table}_{lang} "
                         f"using hnsw (embedding {index.opclass}) with (m = 16, ef_construction = 64)")
            if _has_sparse(index):
                # Inner product is the scoring bge-m3's lexical weights are trained for (RAG review E1).
                conn.execute(f"create index if not exists {table}_{lang}_sparse_hnsw on corpus.{table}_{lang} "
                             f"using hnsw (sparse sparsevec_ip_ops) with (m = 16, ef_construction = 64)")
            conn.commit()
