"""Run a manifest's connectors and persist what they return.

Each source runs in its own thread (hosts differ, so politeness is per connector) with its own
connections. Each document is written in a savepoint and committed on its own, so a document that
fails to persist is rolled back alone, quarantined, and never takes earlier documents with it.
PDFs discovered by the HTML connector are fetched by the PDF connector for the same source.
"""
import logging
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from swiss_grounding.corpus.models import ConnectorResult, SourceSpec
from swiss_grounding.corpus.persist import (
    known_state,
    persist_document,
    promote_due,
    quarantine,
    touch_unchanged,
    upsert_source,
    withdraw,
)
from swiss_grounding.db.connection import connect

log = logging.getLogger(__name__)


def _step(conn, tally: Counter, ok_key: str, what: str, action: Callable[[], None],
          fail_key: str = "failed") -> None:
    """Run one small write in its own transaction, so a failure loses only that write."""
    try:
        with conn.transaction():
            action()
        if ok_key:
            tally[ok_key] += 1
    except Exception:
        log.exception("%s failed", what)
        if fail_key:
            tally[fail_key] += 1


def _persist_result(database_url: str, spec: SourceSpec, result: ConnectorResult, now: datetime,
                    tally: Counter) -> None:
    with connect(database_url) as conn:
        conn.commit()      # close the implicit transaction `connect` opened, so each document commits alone
        for doc in result.documents:
            try:
                with conn.transaction():
                    outcome = persist_document(conn, doc, spec, now)
                tally[outcome] += 1
            except Exception as exc:
                log.exception("persist failed for %s", doc.url)
                tally["failed"] += 1
                _step(conn, tally, "", f"quarantine of {doc.url}",
                      lambda url=doc.url, exc=exc: quarantine(conn, spec.id, url, "persist", repr(exc)),
                      fail_key="")      # the document is already counted as failed
        for url in result.unchanged_urls:
            _step(conn, tally, "unchanged", f"touch of {url}", lambda url=url: touch_unchanged(conn, url, now))
        for url in result.gone_urls:
            _step(conn, tally, "withdrawn", f"withdraw of {url}", lambda url=url: withdraw(conn, url))
        for url, reason in result.errors:
            _step(conn, tally, "failed", f"quarantine of {url}",
                  lambda url=url, reason=reason: quarantine(conn, spec.id, url, "fetch", reason))


def _quarantine_source(database_url: str, spec: SourceSpec, exc: Exception) -> None:
    try:
        with connect(database_url) as conn:
            quarantine(conn, spec.id, f"source:{spec.id}", "fetch", repr(exc))
    except Exception:
        log.exception("could not quarantine failed source %s", spec.id)


def _run_source(database_url: str, spec: SourceSpec, connectors: Mapping, pdf_connector,
                now: Callable[[], datetime]) -> Counter:
    tally: Counter = Counter()
    try:
        with connect(database_url) as conn:
            upsert_source(conn, spec)
            known = known_state(conn, spec.id)
        result = connectors[spec.connector].run(spec, known)
        _persist_result(database_url, spec, result, now(), tally)
        if result.pdfs and pdf_connector is not None:
            _persist_result(database_url, spec, pdf_connector.run_pdfs(spec, result.pdfs, known), now(), tally)
    except Exception as exc:
        log.exception("source %s failed", spec.id)
        tally["failed"] += 1
        _quarantine_source(database_url, spec, exc)
    log.info("source %s: %s", spec.id, dict(tally))
    return tally


def _promote(database_url: str, today) -> Counter:
    try:
        with connect(database_url) as conn:
            promoted = promote_due(conn, today)
    except Exception:
        log.exception("promoting scheduled versions failed; they stay scheduled until the next run")
        return Counter({"promote_failed": 1})
    log.info("promoted %d scheduled versions that came into force", promoted)
    return Counter({"promoted": promoted})


def run_fetch(database_url: str, specs: Sequence[SourceSpec], connectors: Mapping, pdf_connector,
              now: Callable[[], datetime], workers: int = 4) -> dict[str, Counter]:
    """Fetch every source; the report maps source id to outcome counts, plus `_promote`: the
    scheduled versions that came into force and were made current."""
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {spec.id: pool.submit(_run_source, database_url, spec, connectors, pdf_connector, now)
                   for spec in specs}
        report = {sid: future.result() for sid, future in futures.items()}
    return {**report, "_promote": _promote(database_url, now().date())}
