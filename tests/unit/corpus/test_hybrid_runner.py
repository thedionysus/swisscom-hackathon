import threading
import time

import pytest

from swiss_grounding.corpus.hybrid_runner import HybridRunner
from swiss_grounding.corpus.providers import FakeLLM
from swiss_grounding.corpus.runner import BatchRunner, LlmTask

from .test_runner import FakeOpenAI

WAIT_SECONDS = 5


def _tasks(n: int) -> list[LlmTask]:
    return [LlmTask(str(i), "gpt-5-nano", "s", "u") for i in range(n)]


def _wait_for(condition) -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    while not condition() and time.monotonic() < deadline:
        time.sleep(0.01)


def _sync_llm_after_first_batch(client: FakeOpenAI) -> FakeLLM:
    """Direct calls wait until the batch side has submitted a file, so both paths get work."""
    def reply(task):
        _wait_for(lambda: client.submitted)
        return {"ok": task.custom_id}
    return FakeLLM(reply)


def test_every_task_gets_exactly_one_outcome_from_either_path(tmp_path):
    client = FakeOpenAI()
    batch = BatchRunner(client, work_dir=tmp_path, max_per_file=5, poll_seconds=0)
    runner = HybridRunner(batch, _sync_llm_after_first_batch(client), workers=2)
    out = list(runner.run(_tasks(20), kind="describe-chunk"))
    batched = {line["custom_id"] for file in client.submitted for line in file}
    direct = {o.custom_id for o in out if o.sync}
    assert sorted(o.custom_id for o in out) == sorted(str(i) for i in range(20))
    assert batched and direct and batched.isdisjoint(direct)
    assert batched | direct == {str(i) for i in range(20)}
    assert all(o.data == {"ok": o.custom_id} for o in out)


def test_a_batch_is_marked_done_only_after_its_outcomes_were_handed_over(tmp_path):
    """The caller commits each outcome before asking for the next, so `done` may only be signalled
    once every line of that batch has been yielded (the contract of BatchRunner.collect)."""
    client = FakeOpenAI()
    seen: list[str] = []
    early: list[str] = []

    def mark_done(batch_id, status):
        file = client.submitted[int(batch_id.split("-")[-1]) - 1]
        early.extend(line["custom_id"] for line in file if line["custom_id"] not in seen)

    batch = BatchRunner(client, work_dir=tmp_path, max_per_file=3, poll_seconds=0, mark_done=mark_done)
    runner = HybridRunner(batch, _sync_llm_after_first_batch(client), workers=1)
    for outcome in runner.run(_tasks(12), kind="describe-chunk"):
        seen.append(outcome.custom_id)
    assert client.submitted and early == []


def test_a_budget_refusal_before_a_batch_file_stops_both_paths(tmp_path):
    client = FakeOpenAI()
    calls = {"n": 0}
    lock = threading.Lock()

    def before_submit(usd):
        with lock:
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("budget refused")

    def slow_reply(task):
        time.sleep(0.02)
        return {"ok": task.custom_id}

    batch = BatchRunner(client, work_dir=tmp_path, max_per_file=2, poll_seconds=0, before_submit=before_submit)
    runner = HybridRunner(batch, FakeLLM(slow_reply), workers=1)
    out = []
    with pytest.raises(RuntimeError, match="budget refused"):
        out.extend(runner.run(_tasks(200), kind="describe-chunk", estimated_usd=4.0))
    assert len(client.submitted) == 1
    assert len(out) < 200


def test_a_task_list_smaller_than_one_file_still_completes(tmp_path):
    client = FakeOpenAI()
    batch = BatchRunner(client, work_dir=tmp_path, max_per_file=50, poll_seconds=0)
    runner = HybridRunner(batch, FakeLLM(lambda t: {"ok": t.custom_id}), workers=4)
    out = list(runner.run(_tasks(3), kind="describe-doc"))
    assert sorted(o.custom_id for o in out) == ["0", "1", "2"]


def test_no_tasks_yield_nothing(tmp_path):
    batch = BatchRunner(FakeOpenAI(), work_dir=tmp_path, poll_seconds=0)
    assert list(HybridRunner(batch, FakeLLM(lambda t: {}), workers=2).run([], kind="describe-doc")) == []
