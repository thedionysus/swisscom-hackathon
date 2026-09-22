import os
from datetime import UTC, datetime

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.models import FetchError
from swiss_grounding.ingest.pipeline import IngestReport
from swiss_grounding.ingest.run_log import load_source_health, record_run
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources

pytestmark = pytest.mark.integration
T1 = datetime(2026, 9, 10, 1, tzinfo=UTC)
T2 = datetime(2026, 9, 11, 1, tzinfo=UTC)


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        conn.execute("truncate ingest_run")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
    return u


def test_record_and_load_health_uses_latest_run_per_source(url):
    good = IngestReport(source_id="zh_ch", run_id="r1", added=4)
    bad = IngestReport(source_id="zh_ch", run_id="r2", failed=3,
                       errors=(FetchError(url="https://www.zh.ch/x", reason="HTTP 403"),))
    with connect(url) as conn:
        record_run(conn, good, started_at=T1, finished_at=T1)
        record_run(conn, bad, started_at=T2, finished_at=T2)
        health = load_source_health(conn)
    zh = health["zh_ch"]
    assert zh.health == "failing" and zh.last_run_at == T2 and zh.last_successful_run_at == T1
    assert zh.last_run_failed == 3
    assert "ch_ch" not in health


def test_record_run_is_idempotent_per_run_and_source(url):
    report = IngestReport(source_id="ch_ch", run_id="r1", added=1)
    with connect(url) as conn:
        record_run(conn, report, started_at=T1, finished_at=T1)
        record_run(conn, report, started_at=T1, finished_at=T2)
        rows = conn.execute("select finished_at from ingest_run where source_id = 'ch_ch'").fetchall()
    assert len(rows) == 1 and rows[0]["finished_at"] == T2


def test_skipped_documents_are_recorded_with_the_run(url):
    report = IngestReport(source_id="zh_ch", run_id="r9", added=1, skipped=2)
    with connect(url) as conn:
        record_run(conn, report, started_at=T1, finished_at=T1)
        row = conn.execute("select added, skipped from ingest_run where run_id = 'r9'").fetchone()
    assert (row["added"], row["skipped"]) == (1, 2)
