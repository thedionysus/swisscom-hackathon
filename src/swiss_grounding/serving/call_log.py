"""Latency and outcome per tool call. Logging must never break a tool call."""
import logging
from dataclasses import dataclass

import psycopg

from swiss_grounding.db.connection import connect

log = logging.getLogger(__name__)
ABSTAIN = ("no_evidence", "outside_scope", "needs_location", "source_unavailable")
# Keep the write off the hot path: never let a dead or unreachable logging host stall a call.
CONNECT_TIMEOUT_SECONDS = 2
SUMMARY_SQL = """
select tool, count(*) as calls,
       percentile_disc(0.5) within group (order by duration_ms) as p50_ms,
       percentile_disc(0.95) within group (order by duration_ms) as p95_ms,
       avg(case when status = any(%s) then 1.0 else 0.0 end)::float as abstain_rate,
       avg(case when status = 'results' and citations = 0 then 1.0 else 0.0 end)::float as empty_rate
from serving.call_log group by tool order by tool
"""


@dataclass(frozen=True)
class CallRecord:
    tool: str
    duration_ms: int
    status: str
    places: int = 0
    citations: int = 0
    reranker: str | None = None
    error: str | None = None


def record_call(database_url: str, record: CallRecord) -> None:
    try:
        with connect(database_url, connect_timeout=CONNECT_TIMEOUT_SECONDS) as conn:
            conn.execute(
                "insert into serving.call_log (tool, duration_ms, status, places, citations, reranker, error) "
                "values (%s,%s,%s,%s,%s,%s,%s)",
                (record.tool, record.duration_ms, record.status, record.places, record.citations,
                 record.reranker, record.error))
    except psycopg.Error as exc:
        log.warning("call log write failed for %s: %s", record.tool, exc)


def latency_summary(conn: psycopg.Connection) -> list[dict]:
    return conn.execute(SUMMARY_SQL, (list(ABSTAIN),)).fetchall()
