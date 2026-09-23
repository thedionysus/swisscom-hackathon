"""OCR of scanned PDF pages (Task 16).

Chunks with `needs_ocr = true` and no text get one vision task per page image. The transcription is
written into `chunk.text`; `chunk_hash` stays the image digest (it identifies the source page, not the
transcription). Spend is recorded under ledger kind `ocr` for every outcome that billed tokens.

Page images are read when the tasks are built: both runners take a materialised task sequence (the
batch runner serialises every line before splitting files), so a lazy generator would not lower peak
memory. Callers bound memory with `limit`.
"""
import base64
import logging
from collections.abc import Sequence

import psycopg

from swiss_grounding.corpus.budget import OCR_IMAGE_TOKENS, cost_usd, record_spend
from swiss_grounding.corpus.persist import quarantine
from swiss_grounding.corpus.runner import LlmOutcome, LlmTask
from swiss_grounding.db.connection import connect

log = logging.getLogger(__name__)

OCR_SYSTEM = "You transcribe scanned pages of official Swiss documents. Reply with JSON only."
OCR_PROMPT = (
    "Transcribe this scanned page verbatim in its original language. Keep headings, article and paragraph "
    "numbers, list letters and table rows (one row per line, cells separated by ' | '). Do not correct, "
    "translate, summarise or complete anything. Write [illegible] where text cannot be read. "
    'Reply as {"text": "<the transcription>"}.'
)
OCR_OUTPUT_TOKENS = 700          # estimate per page; the cap below leaves room for dense pages and tables
OCR_MAX_OUTPUT_TOKENS = 4000
OCR_PROMPT_TOKENS = 200
PENDING_WHERE = "needs_ocr and text = '' and status in ('current','scheduled')"


def _pending(conn: psycopg.Connection, limit: int | None) -> list[dict]:
    return conn.execute(f"select id, language, ocr_image from corpus.chunk where {PENDING_WHERE} "
                        "order by id limit %s", (limit,)).fetchall()


def _read_image_b64(path: str | None) -> str | None:
    """The page image as base64, or None when the file is gone (paths are relative to the working directory)."""
    if not path:
        return None
    try:
        with open(path, "rb") as handle:
            return base64.b64encode(handle.read()).decode()
    except FileNotFoundError:
        return None


def build_ocr_tasks(conn: psycopg.Connection, model: str, limit: int | None) -> list[LlmTask]:
    """Up to `limit` tasks. A page whose image file is missing is quarantined (stage `ocr`) and skipped, so it
    never uses up the limit; it stays pending, and a later run from the right directory picks it up again.
    Commits when it quarantined anything, so a caller that aborts afterwards (e.g. on budget) keeps the record."""
    tasks: list[LlmTask] = []
    missing = 0
    for row in _pending(conn, None):
        if limit is not None and len(tasks) >= limit:
            break
        image = _read_image_b64(row["ocr_image"])
        if image is None:
            quarantine(conn, "ocr", f"chunk:{row['id']}", "ocr", f"page image missing: {row['ocr_image']}")
            missing += 1
            continue
        tasks.append(LlmTask(custom_id=f"ocr|{row['language']}|{row['id']}", model=model, system=OCR_SYSTEM,
                             user=OCR_PROMPT, image_png_b64=image, max_output_tokens=OCR_MAX_OUTPUT_TOKENS))
    if missing:
        log.warning("ocr: %d page image(s) missing, quarantined (run from the repo root?)", missing)
        conn.commit()
    return tasks


def estimate_ocr(conn: psycopg.Connection, model: str, image_tokens: int = OCR_IMAGE_TOKENS,
                 batch: bool = True) -> float:
    """Price of every pending page. OCR_IMAGE_TOKENS is a placeholder: after the pilot, pass the measured
    input tokens per page as `image_tokens`."""
    pages = conn.execute(f"select count(*) as n from corpus.chunk where {PENDING_WHERE}").fetchone()["n"]
    return pages * cost_usd(model, image_tokens + OCR_PROMPT_TOKENS, OCR_OUTPUT_TOKENS, batch=batch)


def _record(conn: psycopg.Connection, model: str, outcome: LlmOutcome, batch: bool) -> None:
    if outcome.input_tokens or outcome.output_tokens:
        record_spend(conn, kind="ocr", model=model,
                     usd=cost_usd(model, outcome.input_tokens, outcome.output_tokens, batch=batch),
                     input_tokens=outcome.input_tokens, output_tokens=outcome.output_tokens, estimated=False)


def _transcription(outcome: LlmOutcome) -> str | None:
    text = outcome.data.get("text") if isinstance(outcome.data, dict) else None
    return text.strip() if isinstance(text, str) and text.strip() else None


def _already_done(conn: psycopg.Connection, chunk_id: int, language: str) -> bool:
    """A resumed batch can replay an outcome that was already ingested."""
    row = conn.execute("select needs_ocr from corpus.chunk where id = %s and language = %s",
                       (chunk_id, language)).fetchone()
    return row is not None and not row["needs_ocr"]


def _write_text(conn: psycopg.Connection, chunk_id: int, language: str, text: str) -> bool:
    row = conn.execute("update corpus.chunk set text = %s, needs_ocr = false "
                       "where id = %s and language = %s and needs_ocr returning document_id",
                       (text, chunk_id, language)).fetchone()
    if row is None:
        return False
    conn.execute("update corpus.document set extraction = 'ocr' where id = %s", (row["document_id"],))
    conn.execute("delete from corpus.quarantine where source_id = 'ocr' and url = %s and stage = 'ocr'",
                 (f"chunk:{chunk_id}",))
    return True


def run_ocr(database_url: str, runner, tasks: Sequence[LlmTask], model: str, batch: bool,
            estimated_usd: float = 0.0) -> dict[str, int]:
    """Run the tasks and write each transcription. Commits after every outcome, since the batch
    runner marks a batch ingested only once its last outcome has been consumed."""
    report = {"done": 0, "failed": 0, "skipped": 0}
    with connect(database_url) as conn:
        for outcome in runner.run(tasks, kind="ocr", estimated_usd=estimated_usd):
            _, language, chunk_id = outcome.custom_id.split("|")
            if _already_done(conn, int(chunk_id), language):
                report["skipped"] += 1
                continue
            _record(conn, model, outcome, batch)
            text = _transcription(outcome)
            if text is None:
                quarantine(conn, "ocr", f"chunk:{chunk_id}", "ocr", outcome.error or "empty transcription")
                report["failed"] += 1
            elif _write_text(conn, int(chunk_id), language, text):
                report["done"] += 1
            else:
                quarantine(conn, "ocr", f"chunk:{chunk_id}", "ocr", "chunk no longer pending OCR")
                report["failed"] += 1
            conn.commit()
    return report
