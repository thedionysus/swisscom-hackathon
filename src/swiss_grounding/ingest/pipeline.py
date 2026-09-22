import logging
from dataclasses import dataclass, replace

import psycopg

from swiss_grounding.ingest.chunking import ChunkLimits, chunk_sections
from swiss_grounding.ingest.context import describe_chunks
from swiss_grounding.ingest.enrich import document_text, enrich
from swiss_grounding.ingest.fetch_state import load_known
from swiss_grounding.ingest.fetchers.base import Fetcher
from swiss_grounding.ingest.llm import LLM
from swiss_grounding.ingest.models import FetchError
from swiss_grounding.ingest.persist import (
    SKIPPED,
    mark_withdrawn,
    persist_document,
    touch_unchanged,
)
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.categories import CATEGORIES
from swiss_grounding.registry.models import Source
from swiss_grounding.retrieval.embedder import Embedder

log = logging.getLogger(__name__)
DEFAULT_LIMITS = ChunkLimits()


@dataclass(frozen=True)
class IngestReport:
    source_id: str
    run_id: str
    added: int = 0
    modified: int = 0
    unchanged: int = 0
    withdrawn: int = 0
    skipped: int = 0        # held nothing worth indexing; not a success, and not a retryable failure
    failed: int = 0
    errors: tuple[FetchError, ...] = ()

    def bump(self, field: str, error: FetchError | None = None) -> "IngestReport":
        errors = self.errors + ((error,) if error else ())
        return replace(self, **{field: getattr(self, field) + 1, "errors": errors})


def run_ingest(conn: psycopg.Connection, source: Source, fetcher: Fetcher, llm: LLM, embedder: Embedder,
               tree: LocationTree, run_id: str, limits: ChunkLimits = DEFAULT_LIMITS) -> IngestReport:
    """Run one source through fetch → enrich → chunk → describe → persist.

    Failures are per document. `describe_chunks` is where the model calls of ADR 0005 are made and
    where page furniture is dropped, so a document that was nothing but furniture arrives at
    `persist_document` with no chunks and is recorded as skipped, not as a failure.
    """
    report = IngestReport(source_id=source.id, run_id=run_id)
    known = load_known(conn, source.id)
    result = fetcher.fetch(source, known)
    for error in result.errors:
        log.warning("fetch failed source=%s url=%s reason=%s", source.id, error.url, error.reason)
        report = report.bump("failed", error)
    for url in result.unchanged_urls:
        touch_unchanged(conn, url)
        report = report.bump("unchanged")
    for url in result.gone_urls:
        if mark_withdrawn(conn, url, run_id):
            report = report.bump("withdrawn")
    for fetched in result.documents:
        try:
            with conn.transaction():
                enriched = enrich(fetched, source, tree, llm)
                chunks = chunk_sections(fetched.sections, enriched.sections_en, limits)
                described = describe_chunks(
                    chunks, source=source, title_en=enriched.title_en,
                    document_text_en=document_text(enriched), llm=llm, categories=CATEGORIES,
                )
                outcome = persist_document(conn, enriched, described.kept, embedder, run_id)
        except Exception as exc:
            log.exception("ingest failed source=%s url=%s", source.id, fetched.url)
            report = report.bump("failed", FetchError(url=fetched.url, reason=str(exc)))
            continue
        if outcome.change_type == SKIPPED:
            log.info("nothing to index source=%s url=%s", source.id, fetched.url)
        report = report.bump(outcome.change_type or "unchanged")
    log.info("ingest done %s", report)
    return report
