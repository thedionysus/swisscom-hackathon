from datetime import UTC, datetime

from swiss_grounding.ingest.run_log import RunRow, summarize_health

T1 = datetime(2026, 9, 10, tzinfo=UTC)
T2 = datetime(2026, 9, 11, tzinfo=UTC)


def run(finished, *, added=0, modified=0, unchanged=0, failed=0, withdrawn=0) -> RunRow:
    return RunRow(run_id=finished.isoformat(), source_id="zh_ch", started_at=finished, finished_at=finished,
                  added=added, modified=modified, unchanged=unchanged, withdrawn=withdrawn, failed=failed)


def test_no_runs_is_unknown():
    h = summarize_health("zh_ch", ())
    assert h.health == "unknown" and h.last_run_at is None and h.last_successful_run_at is None
    assert h.last_run_failed == 0


def test_last_run_without_failures_is_ok():
    h = summarize_health("zh_ch", (run(T2, unchanged=5), run(T1, failed=3)))
    assert h.health == "ok" and h.last_run_at == T2 and h.last_successful_run_at == T2 and h.last_run_failed == 0


def test_failures_with_some_success_is_degraded():
    h = summarize_health("zh_ch", (run(T2, added=1, failed=2),))
    assert h.health == "degraded" and h.last_successful_run_at == T2 and h.last_run_failed == 2


def test_only_failures_is_failing_and_keeps_previous_success():
    h = summarize_health("zh_ch", (run(T2, failed=3), run(T1, added=4)))
    assert h.health == "failing" and h.last_run_at == T2 and h.last_successful_run_at == T1
    assert h.last_run_failed == 3


def test_failing_with_no_prior_success_has_no_successful_run():
    h = summarize_health("zh_ch", (run(T2, failed=3),))
    assert h.health == "failing" and h.last_successful_run_at is None
