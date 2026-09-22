"""Per-source ingest run bookkeeping and the fetch-health signal derived from it."""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import psycopg

from swiss_grounding.ingest.pipeline import IngestReport

Health = Literal["ok", "degraded", "failing", "unknown"]

UPSERT = """
insert into ingest_run (run_id, source_id, started_at, finished_at, added, modified, unchanged,
                        withdrawn, skipped, failed)
values (%(run_id)s, %(source_id)s, %(started_at)s, %(finished_at)s, %(added)s, %(modified)s, %(unchanged)s,
        %(withdrawn)s, %(skipped)s, %(failed)s)
on conflict (run_id, source_id) do update set started_at = excluded.started_at,
    finished_at = excluded.finished_at, added = excluded.added, modified = excluded.modified,
    unchanged = excluded.unchanged, withdrawn = excluded.withdrawn, skipped = excluded.skipped,
    failed = excluded.failed
"""
SELECT_RUNS = """
select run_id, source_id, started_at, finished_at, added, modified, unchanged, withdrawn, skipped, failed
from ingest_run order by source_id, finished_at desc
"""


@dataclass(frozen=True)
class RunRow:
    run_id: str
    source_id: str
    started_at: datetime
    finished_at: datetime
    added: int
    modified: int
    unchanged: int
    withdrawn: int
    failed: int
    skipped: int = 0

    @property
    def succeeded_any(self) -> bool:
        """A skip counts: the pipeline reached a verdict on that document, it just held nothing."""
        return (self.added + self.modified + self.unchanged + self.skipped) > 0


@dataclass(frozen=True)
class SourceHealth:
    source_id: str
    last_run_at: datetime | None
    last_successful_run_at: datetime | None
    last_run_failed: int
    health: Health


def health_of(run: RunRow | None) -> Health:
    """ok: no failures. degraded: failures but some documents came through. failing: only failures."""
    if run is None:
        return "unknown"
    if run.failed == 0:
        return "ok"
    return "degraded" if run.succeeded_any else "failing"


def summarize_health(source_id: str, runs: Sequence[RunRow]) -> SourceHealth:
    """Runs must be ordered newest first. A successful run is one that is ok or degraded."""
    latest = runs[0] if runs else None
    successful = next((r.finished_at for r in runs if health_of(r) in ("ok", "degraded")), None)
    return SourceHealth(
        source_id=source_id,
        last_run_at=latest.finished_at if latest else None,
        last_successful_run_at=successful,
        last_run_failed=latest.failed if latest else 0,
        health=health_of(latest),
    )


def record_run(conn: psycopg.Connection, report: IngestReport, started_at: datetime, finished_at: datetime) -> None:
    conn.execute(UPSERT, {
        "run_id": report.run_id, "source_id": report.source_id, "started_at": started_at,
        "finished_at": finished_at, "added": report.added, "modified": report.modified,
        "unchanged": report.unchanged, "withdrawn": report.withdrawn, "skipped": report.skipped,
        "failed": report.failed,
    })


def load_source_health(conn: psycopg.Connection) -> Mapping[str, SourceHealth]:
    rows = tuple(RunRow(**r) for r in conn.execute(SELECT_RUNS).fetchall())
    source_ids = tuple(dict.fromkeys(r.source_id for r in rows))
    return {sid: summarize_health(sid, tuple(r for r in rows if r.source_id == sid)) for sid in source_ids}
