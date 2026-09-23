import json

import httpx
import pytest
from openai import APIConnectionError

from swiss_grounding.corpus.providers import FakeLLM, ReplyError, Usage
from swiss_grounding.corpus.runner import BatchRunner, LlmTask, SyncRunner, parse_batch_line


def test_sync_runner_returns_one_outcome_per_task():
    runner = SyncRunner(FakeLLM(lambda t: {"id": t.custom_id}), workers=2)
    out = list(runner.run([LlmTask("a", "m", "s", "u"), LlmTask("b", "m", "s", "u")]))
    assert sorted(o.custom_id for o in out) == ["a", "b"]
    assert all(o.data == {"id": o.custom_id} for o in out)


def test_sync_runner_accepts_and_ignores_estimated_usd():
    runner = SyncRunner(FakeLLM(lambda t: {"id": t.custom_id}), workers=1)
    out = list(runner.run([LlmTask("a", "m", "s", "u")], kind="describe", estimated_usd=12.5))
    assert [o.custom_id for o in out] == ["a"]


def test_sync_runner_turns_exceptions_into_errors():
    def boom(task):
        raise ValueError("bad reply")
    [out] = SyncRunner(FakeLLM(boom), workers=1).run([LlmTask("a", "m", "s", "u")])
    assert out.data is None and "bad reply" in out.error


class _RaisingReplyLLM:
    """Simulates OpenAILLM/AnthropicLLM raising ReplyError after billing tokens."""

    def complete(self, task):
        raise ReplyError("unparseable reply: no JSON object in model reply", Usage(42, 7))


def test_sync_runner_keeps_billed_usage_on_an_unparseable_reply():
    [out] = SyncRunner(_RaisingReplyLLM(), workers=1).run([LlmTask("a", "m", "s", "u")])
    assert out.data is None
    assert out.input_tokens == 42 and out.output_tokens == 7
    assert "unparseable reply" in out.error


def test_parse_batch_line_for_chat_completion():
    line = {"custom_id": "a", "response": {"status_code": 200, "body": {
        "choices": [{"message": {"content": '{"x": 1}'}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}}}
    out = parse_batch_line(json.dumps(line))
    assert out.data == {"x": 1} and out.input_tokens == 10 and out.output_tokens == 5


def test_parse_batch_line_error():
    out = parse_batch_line(json.dumps({"custom_id": "a", "response": None, "error": {"message": "rate"}}))
    assert out.data is None and "rate" in out.error


class FakeOpenAI:
    """Stands in for the openai client's files and batches resources.

    `statuses` maps a batch id to a terminal status other than "completed" (e.g. "failed"), to
    simulate a batch that OpenAI rejected at validation (no output file).
    """

    def __init__(self, statuses: dict[str, str] | None = None):
        self.submitted = []
        self.statuses = statuses or {}
        outer = self

        class Files:
            def create(self, file, purpose):
                outer.submitted.append([json.loads(line) for line in file.read().decode().splitlines()])
                return type("F", (), {"id": f"file-{len(outer.submitted)}"})()

            def content(self, file_id):
                n = int(file_id.split("-")[-1])
                lines = [json.dumps({"custom_id": r["custom_id"], "response": {"status_code": 200, "body": {
                    "choices": [{"message": {"content": json.dumps({"ok": r["custom_id"]})}}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 2}}}}) for r in outer.submitted[n - 1]]
                return type("C", (), {"text": "\n".join(lines)})()

        class Batches:
            def create(self, input_file_id, endpoint, completion_window):
                return type("B", (), {"id": "batch-" + input_file_id.split("-")[-1]})()

            def retrieve(self, batch_id):
                n = batch_id.split("-")[-1]
                status = outer.statuses.get(batch_id, "completed")
                if status != "completed":
                    return type("B", (), {"status": status, "output_file_id": None, "error_file_id": None,
                                          "errors": {"message": "Enqueued token limit reached"}})()
                return type("B", (), {"status": "completed", "output_file_id": f"out-{n}", "error_file_id": None})()

        self.files, self.batches = Files(), Batches()


def test_batch_runner_splits_files_and_collects_results(tmp_path):
    client = FakeOpenAI()
    records = []
    runner = BatchRunner(client, work_dir=tmp_path, max_per_file=2, poll_seconds=0,
                         record=lambda *a: records.append(a))
    tasks = [LlmTask(str(i), "gpt-5-nano", "s", "u") for i in range(5)]
    out = list(runner.run(tasks, kind="describe", estimated_usd=10.0))
    assert len(client.submitted) == 3
    assert sorted(o.custom_id for o in out) == ["0", "1", "2", "3", "4"]
    assert all(o.data == {"ok": o.custom_id} for o in out)
    # request_count matches file split, and estimate is split pro rata by line count.
    assert sorted(r[3] for r in records) == [1, 2, 2]
    assert sum(r[5] for r in records) == 10.0


def test_batch_runner_marks_batches_done_after_collecting(tmp_path):
    client = FakeOpenAI()
    done = []
    runner = BatchRunner(client, work_dir=tmp_path, max_per_file=50, poll_seconds=0,
                         record=lambda *a: None, mark_done=lambda batch_id, status: done.append((batch_id, status)))
    tasks = [LlmTask("0", "gpt-5-nano", "s", "u")]
    list(runner.run(tasks, kind="describe"))
    assert done == [("batch-1", "completed")]


def test_submit_lines_splits_on_max_bytes(tmp_path):
    client = FakeOpenAI()
    lines = [{"custom_id": str(i), "body": "x" * 40} for i in range(4)]
    runner = BatchRunner(client, work_dir=tmp_path, max_per_file=100, max_bytes=120, poll_seconds=0,
                         record=lambda *a: None)
    batch_ids = runner.submit_lines(lines, kind="describe", endpoint="/v1/chat/completions")
    assert len(batch_ids) > 1
    assert sum(len(f) for f in client.submitted) == 4


def test_submit_lines_splits_on_max_tokens_per_file(tmp_path):
    """A line's estimated input tokens (system + user text) also forces a new file, so a run
    never enqueues more than one file's worth of tokens at a time against the org's queue limit."""
    client = FakeOpenAI()
    runner = BatchRunner(client, work_dir=tmp_path, max_per_file=100, max_bytes=10**9, max_tokens_per_file=100,
                         poll_seconds=0, record=lambda *a: None)
    lines = [{"custom_id": str(i), "method": "POST", "url": "/v1/chat/completions",
              "body": {"model": "gpt-5-nano",
                       "messages": [{"role": "system", "content": ""}, {"role": "user", "content": "x" * 150}]}}
             for i in range(3)]
    batch_ids = runner.submit_lines(lines, kind="describe", endpoint="/v1/chat/completions")
    assert len(batch_ids) == 2
    assert [len(f) for f in client.submitted] == [2, 1]


def test_resume_collects_already_submitted_batches(tmp_path):
    client = FakeOpenAI()
    runner = BatchRunner(client, work_dir=tmp_path, max_per_file=50, poll_seconds=0, record=lambda *a: None)
    tasks = [LlmTask(str(i), "gpt-5-nano", "s", "u") for i in range(3)]
    lines = [{"custom_id": t.custom_id, "method": "POST", "url": "/v1/chat/completions",
              "body": {"model": t.model}} for t in tasks]
    batch_ids = runner.submit_lines(lines, kind="describe", endpoint="/v1/chat/completions")
    out = list(runner.resume(batch_ids))
    assert sorted(o.custom_id for o in out) == ["0", "1", "2"]
    assert all(o.data == {"ok": o.custom_id} for o in out)


def test_run_reports_missing_outcomes_for_a_failed_batch_and_continues(tmp_path):
    """A batch that OpenAI fails at validation (e.g. the enqueued token limit) produces no output
    file; every custom id that was in it gets an error outcome instead of silently vanishing, and
    the next file is still submitted and collected."""
    client = FakeOpenAI(statuses={"batch-1": "failed"})
    runner = BatchRunner(client, work_dir=tmp_path, max_per_file=2, poll_seconds=0, record=lambda *a: None)
    tasks = [LlmTask(str(i), "gpt-5-nano", "s", "u") for i in range(4)]
    out = list(runner.run(tasks, kind="describe"))
    assert len(client.submitted) == 2

    failed = {o.custom_id: o for o in out if o.custom_id in {"0", "1"}}
    assert set(failed) == {"0", "1"}
    assert all(o.data is None and "no result: batch batch-1 failed" in o.error for o in failed.values())

    succeeded = {o.custom_id: o for o in out if o.custom_id in {"2", "3"}}
    assert set(succeeded) == {"2", "3"}
    assert all(o.data == {"ok": o.custom_id} for o in succeeded.values())


def test_resume_reports_missing_outcomes_for_a_failed_batch_when_input_is_known(tmp_path):
    client = FakeOpenAI(statuses={"batch-1": "failed"})
    runner = BatchRunner(client, work_dir=tmp_path, max_per_file=50, poll_seconds=0, record=lambda *a: None)
    lines = [{"custom_id": "0", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "gpt-5-nano"}}]
    batch_ids = runner.submit_lines(lines, kind="describe", endpoint="/v1/chat/completions")
    out = list(runner.resume(batch_ids))
    assert len(out) == 1 and out[0].custom_id == "0" and out[0].data is None
    assert "no result: batch batch-1 failed" in out[0].error


def test_resume_logs_when_a_failed_batchs_input_is_not_known_locally(tmp_path, caplog):
    client = FakeOpenAI(statuses={"batch-9": "failed"})
    runner = BatchRunner(client, work_dir=tmp_path, poll_seconds=0, record=lambda *a: None)
    with caplog.at_level("WARNING"):
        out = list(runner.resume(["batch-9"]))
    assert out == []
    assert any("batch-9" in record.message for record in caplog.records)


def test_submit_logs_and_reraises_when_record_fails(tmp_path, caplog):
    client = FakeOpenAI()

    def bad_record(*args):
        raise RuntimeError("db down")

    runner = BatchRunner(client, work_dir=tmp_path, max_per_file=50, poll_seconds=0, record=bad_record)
    tasks = [LlmTask("0", "gpt-5-nano", "s", "u")]
    with caplog.at_level("ERROR"), pytest.raises(RuntimeError, match="db down"):
        list(runner.run(tasks, kind="describe"))
    assert any("batch-1" in record.message for record in caplog.records)


def test_submit_appends_to_submitted_log_before_recording(tmp_path):
    client = FakeOpenAI()
    runner = BatchRunner(client, work_dir=tmp_path, max_per_file=50, poll_seconds=0, record=lambda *a: None)
    tasks = [LlmTask("0", "gpt-5-nano", "s", "u")]
    list(runner.run(tasks, kind="describe"))
    content = (tmp_path / "submitted.log").read_text(encoding="utf-8")
    assert "batch-1 describe" in content


def test_collect_retries_after_a_network_error(tmp_path):
    client = FakeOpenAI()
    calls = {"n": 0}
    real_retrieve = client.batches.retrieve

    def flaky(batch_id):
        calls["n"] += 1
        if calls["n"] == 1:
            raise APIConnectionError(request=httpx.Request("GET", "https://api.openai.com"))
        return real_retrieve(batch_id)

    client.batches.retrieve = flaky
    runner = BatchRunner(client, work_dir=tmp_path, max_per_file=50, poll_seconds=0, record=lambda *a: None)
    tasks = [LlmTask("0", "gpt-5-nano", "s", "u")]
    out = list(runner.run(tasks, kind="describe"))
    assert out[0].data == {"ok": "0"}
    assert calls["n"] == 2


def test_fetch_then_done_marks_the_batch_only_when_told(tmp_path):
    """Embedding ingestion commits in blocks, so it fetches a batch's lines and signals `done`
    itself once the last block is committed."""
    client = FakeOpenAI()
    done = []
    runner = BatchRunner(client, work_dir=tmp_path, poll_seconds=0,
                         mark_done=lambda batch_id, status: done.append((batch_id, status)))
    [(batch_id, group)] = list(runner.submit_sequentially(
        [{"custom_id": "a", "method": "POST", "url": "/v1/chat/completions", "body": {}}], "embed",
        "/v1/chat/completions", estimated_usd=1.0))
    assert [line["custom_id"] for line in group] == ["a"]
    lines = runner.fetch(batch_id)
    assert len(lines) == 1 and done == []
    runner.done(batch_id)
    assert done == [(batch_id, "completed")]


def test_submit_sequentially_submits_the_next_file_only_when_asked(tmp_path):
    client = FakeOpenAI()
    runner = BatchRunner(client, work_dir=tmp_path, max_per_file=1, poll_seconds=0)
    lines = [{"custom_id": str(i), "method": "POST", "url": "/v1/embeddings", "body": {"input": "x"}}
             for i in range(3)]
    gen = runner.submit_sequentially(lines, "embed", "/v1/embeddings")
    next(gen)
    assert len(client.submitted) == 1
    assert len(list(gen)) == 2 and len(client.submitted) == 3
