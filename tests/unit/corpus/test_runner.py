import json

from swiss_grounding.corpus.providers import FakeLLM
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


def test_parse_batch_line_for_chat_completion():
    line = {"custom_id": "a", "response": {"status_code": 200, "body": {
        "choices": [{"message": {"content": '{"x": 1}'}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}}}
    out = parse_batch_line(json.dumps(line))
    assert out.data == {"x": 1} and out.input_tokens == 10 and out.output_tokens == 5


def test_parse_batch_line_error():
    out = parse_batch_line(json.dumps({"custom_id": "a", "response": None, "error": {"message": "rate"}}))
    assert out.data is None and "rate" in out.error


class FakeOpenAI:
    """Stands in for the openai client's files and batches resources."""
    def __init__(self):
        self.submitted = []
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


def test_batch_runner_marks_batches_done_after_collecting():
    client = FakeOpenAI()
    done = []
    runner = BatchRunner(client, work_dir="/tmp", max_per_file=50, poll_seconds=0,
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
