import json
import logging
import time
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LlmTask:
    custom_id: str
    model: str
    system: str
    user: str
    image_png_b64: str | None = None
    max_output_tokens: int = 800


@dataclass(frozen=True)
class LlmOutcome:
    custom_id: str
    data: dict | None
    input_tokens: int
    output_tokens: int
    error: str | None = None


log = logging.getLogger(__name__)
CHAT_ENDPOINT = "/v1/chat/completions"
EMBEDDINGS_ENDPOINT = "/v1/embeddings"
TERMINAL = {"completed", "failed", "expired", "cancelled"}


class SyncRunner:
    def __init__(self, llm, workers: int = 8):
        self._llm = llm
        self._workers = workers

    def run(self, tasks: Sequence[LlmTask], kind: str = "", estimated_usd: float = 0.0) -> Iterator[LlmOutcome]:
        """`kind` and `estimated_usd` are accepted (and ignored) so callers can share one
        signature with `BatchRunner.run` regardless of which runner they hold."""
        def one(task: LlmTask) -> LlmOutcome:
            try:
                data, usage = self._llm.complete(task)
                return LlmOutcome(task.custom_id, data, usage.input_tokens, usage.output_tokens)
            except Exception as exc:  # noqa: BLE001 - any provider failure becomes a per-task error outcome
                return LlmOutcome(task.custom_id, None, 0, 0, error=repr(exc))
        with ThreadPoolExecutor(max_workers=self._workers) as pool:
            for future in as_completed([pool.submit(one, t) for t in tasks]):
                yield future.result()


def parse_batch_line(line: str) -> LlmOutcome:
    from swiss_grounding.corpus.providers import extract_json
    record = json.loads(line)
    custom_id = record["custom_id"]
    response = record.get("response")
    if not response or response.get("status_code") != 200:
        message = (record.get("error") or {}).get("message") or json.dumps(response)[:300]
        return LlmOutcome(custom_id, None, 0, 0, error=message)
    body = response["body"]
    usage = body.get("usage", {})
    try:
        data = extract_json(body["choices"][0]["message"]["content"] or "")
    except (ValueError, KeyError, IndexError) as exc:
        return LlmOutcome(custom_id, None, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
                          error=f"unparseable reply: {exc}")
    return LlmOutcome(custom_id, data, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))


class BatchRunner:
    """OpenAI Batch API: half price, results within 24 hours.

    `record(batch_id, kind, endpoint, request_count, input_path, estimated_usd)` is called after
    each submission so the CLI can store it in corpus.batch_job; `mark_done(batch_id, status)` is
    called once a batch's results have been fully yielded from `collect`. `resume(batch_ids)`
    re-attaches to batches already submitted by an earlier, interrupted run.
    """

    def __init__(self, client, work_dir: Path | str, max_per_file: int = 50_000, max_bytes: int = 150_000_000,
                poll_seconds: float = 60, record: Callable[..., None] = lambda *a: None,
                mark_done: Callable[[str, str], None] = lambda *a: None,
                sleep: Callable[[float], None] = time.sleep):
        self._client = client
        self._dir = Path(work_dir)
        self._max = max_per_file
        self._max_bytes = max_bytes
        self._poll = poll_seconds
        self._record = record
        self._mark_done = mark_done
        self._sleep = sleep

    def _submit(self, lines: list[dict], kind: str, endpoint: str, index: int, estimated_usd: float) -> str:
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / f"{kind}-{int(time.time())}-{index}.jsonl"
        path.write_text("\n".join(json.dumps(line, ensure_ascii=False) for line in lines))
        with path.open("rb") as handle:
            uploaded = self._client.files.create(file=handle, purpose="batch")
        batch = self._client.batches.create(input_file_id=uploaded.id, endpoint=endpoint, completion_window="24h")
        self._record(batch.id, kind, endpoint, len(lines), str(path), estimated_usd)
        log.info("submitted %s batch %s with %d requests", kind, batch.id, len(lines))
        return batch.id

    def collect(self, batch_id: str) -> Iterator[str]:
        """Wait for one batch and yield its raw result lines (successes and errors), then mark
        it done (A3) so a later `ensure_within` no longer counts it as in flight."""
        while True:
            batch = self._client.batches.retrieve(batch_id)
            if batch.status in TERMINAL:
                break
            self._sleep(self._poll)
        lines: list[str] = []
        for file_id in (batch.output_file_id, getattr(batch, "error_file_id", None)):
            if file_id:
                lines.extend(line for line in self._client.files.content(file_id).text.splitlines() if line.strip())
        yield from lines
        self._mark_done(batch_id, batch.status)

    def _group_lines(self, lines: Sequence[dict]) -> list[list[dict]]:
        """A4: a new file starts when adding a line would pass `max_bytes` or `max_per_file`."""
        groups: list[list[dict]] = []
        current: list[dict] = []
        current_bytes = 0
        for line in lines:
            encoded_len = len(json.dumps(line, ensure_ascii=False).encode("utf-8")) + 1
            if current and (len(current) >= self._max or current_bytes + encoded_len > self._max_bytes):
                groups.append(current)
                current, current_bytes = [], 0
            current.append(line)
            current_bytes += encoded_len
        if current:
            groups.append(current)
        return groups

    def submit_lines(self, lines: Sequence[dict], kind: str, endpoint: str, estimated_usd: float = 0.0) -> list[str]:
        groups = self._group_lines(lines)
        total = len(lines)
        return [self._submit(group, kind, endpoint, index, estimated_usd * (len(group) / total) if total else 0.0)
                for index, group in enumerate(groups)]

    def resume(self, batch_ids: Sequence[str]) -> Iterator[LlmOutcome]:
        """Re-attach to batches already submitted (by this run or a prior, interrupted one)."""
        for batch_id in batch_ids:
            for line in self.collect(batch_id):
                yield parse_batch_line(line)

    def run(self, tasks: Sequence[LlmTask], kind: str, estimated_usd: float = 0.0) -> Iterator[LlmOutcome]:
        from swiss_grounding.corpus.providers import OpenAILLM
        lines = [{"custom_id": t.custom_id, "method": "POST", "url": CHAT_ENDPOINT, "body": OpenAILLM.chat_body(t)}
                 for t in tasks]
        batch_ids = self.submit_lines(lines, kind, CHAT_ENDPOINT, estimated_usd)
        yield from self.resume(batch_ids)
