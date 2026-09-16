"""Persist probe results so runs can be diffed by commit."""
import json
from collections.abc import Sequence

import psycopg

from swiss_grounding.evals.runner import ProbeResult

INSERT = """
insert into eval_run (run_id, git_commit, tier, probe_id, kind, failure_class, passed, failures, observed)
values (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
"""

SUMMARY = """
select run_id, count(*)::int as total, count(*) filter (where passed)::int as passed,
       count(*) filter (where not passed)::int as failed
from eval_run
where run_id = (select run_id from eval_run order by ran_at desc, id desc limit 1)
group by run_id
"""


def insert_results(conn: psycopg.Connection, run_id: str, git_commit: str | None, tier: str,
                   results: Sequence[ProbeResult]) -> None:
    for r in results:
        conn.execute(INSERT, (
            run_id, git_commit, tier, r.probe.id, r.probe.kind, r.probe.failure_class, r.passed,
            json.dumps(list(r.failures)), r.observed.model_dump_json(),
        ))


def latest_run_summary(conn: psycopg.Connection) -> dict | None:
    row = conn.execute(SUMMARY).fetchone()
    return dict(row) if row else None
