import json
import logging
import time
import uuid
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from openai import APIConnectionError, APITimeoutError


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
    sync: bool = False          # a direct call (twice the batch price), not a Batch API result


log = logging.getLogger(__name__)
CHAT_ENDPOINT = "/v1/chat/completions"
EMBEDDINGS_ENDPOINT = "/v1/embeddings"
TERMINAL = {"completed", "failed", "expired", "cancelled"}
NON_SUCCESS_STATUSES = {"failed", "expired", "cancelled"}
# Files are filled to this share of max_tokens_per_file: OpenAI counts the queue with its own tokenizer.
BATCH_TOKEN_HEADROOM = 0.95


def complete_one(llm, task: LlmTask) -> LlmOutcome:
    """One direct call as an outcome: provider failures become per-task errors, never exceptions."""
    from swiss_grounding.corpus.providers import ReplyError
    try:
        data, usage = llm.complete(task)
        return LlmOutcome(task.custom_id, data, usage.input_tokens, usage.output_tokens, sync=True)
    except ReplyError as exc:
        # A paid reply that failed to parse still billed tokens; keep them on the outcome.
        return LlmOutcome(task.custom_id, None, exc.usage.input_tokens, exc.usage.output_tokens,
                          error=str(exc), sync=True)
    except Exception as exc:  # noqa: BLE001 - any provider failure becomes a per-task error outcome
        return LlmOutcome(task.custom_id, None, 0, 0, error=repr(exc), sync=True)


class SyncRunner:
    def __init__(self, llm, workers: int = 8):
        self._llm = llm
        self._workers = workers

    def run(self, tasks: Sequence[LlmTask], kind: str = "", estimated_usd: float = 0.0) -> Iterator[LlmOutcome]:
        """`kind` and `estimated_usd` are accepted (and ignored) so callers can share one
        signature with `BatchRunner.run` regardless of which runner they hold."""
        with ThreadPoolExecutor(max_workers=self._workers) as pool:
            for future in as_completed([pool.submit(complete_one, self._llm, t) for t in tasks]):
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


def chat_line(task: LlmTask) -> dict:
    from swiss_grounding.corpus.providers import OpenAILLM
    return {"custom_id": task.custom_id, "method": "POST", "url": CHAT_ENDPOINT, "body": OpenAILLM.chat_body(task)}


def _line_input_tokens(line: dict) -> int:
    """A batch line's input tokens for the enqueued-token-limit split (chat lines: system + user text,
    plus OCR_IMAGE_TOKENS when the user content carries an image; embedding lines: their `input` text),
    counted with the model's tokenizer."""
    from swiss_grounding.corpus.budget import OCR_IMAGE_TOKENS
    from swiss_grounding.corpus.tokens import count_tokens

    body = line.get("body", {})
    if "messages" in body:
        messages = body["messages"]
        system = messages[0].get("content", "") if messages else ""
        content = messages[1].get("content", "") if len(messages) > 1 else ""
        has_image = False
        if isinstance(content, list):
            text = " ".join(part.get("text", "") for part in content if part.get("type") == "text")
            has_image = any(part.get("type") == "image_url" for part in content)
        else:
            text = content
        tokens = count_tokens(f"{system}{text}")
        return tokens + OCR_IMAGE_TOKENS if has_image else tokens
    if "input" in body:
        return count_tokens(body["input"])
    return 0


class FileBudget:
    """Admits lines into one Batch file until the next would pass the item, byte or token limit.
    The first line is always admitted, so an oversized line still gets a file of its own."""

    def __init__(self, max_items: int, max_bytes: int, max_tokens: float):
        self._limits = (max_items, max_bytes, max_tokens)
        self.items, self.bytes, self.tokens = 0, 0, 0

    def admit(self, line: dict) -> bool:
        encoded_len = len(json.dumps(line, ensure_ascii=False).encode("utf-8")) + 1
        tokens = _line_input_tokens(line)
        max_items, max_bytes, max_tokens = self._limits
        if self.items and (self.items >= max_items or self.bytes + encoded_len > max_bytes
                           or self.tokens + tokens > max_tokens):
            return False
        self.items, self.bytes, self.tokens = self.items + 1, self.bytes + encoded_len, self.tokens + tokens
        return True


class BatchRunner:
    """OpenAI Batch API: half price, results within 24 hours.

    `record(batch_id, kind, endpoint, request_count, input_path, estimated_usd)` is called after
    each submission so the CLI can store it in corpus.batch_job. `mark_done(batch_id, status)` is
    called by `collect()` only once every one of that batch's result lines has been pulled from the
    generator by the caller — callers must have committed the outcome of each yielded line (or at
    least be certain they will) before asking for the next one, since `mark_done` is the signal that
    this batch no longer counts as "in flight" for `budget.ensure_within` (A3). `resume(batch_ids)`
    re-attaches to batches already submitted by an earlier, interrupted run. `before_submit(file_usd)`
    runs before each file of `run()`/`submit_sequentially()` is submitted; raising stops the run there.

    `run()` submits and collects one file at a time (rather than all of them up front) so the
    org's per-model enqueued-token limit is never exceeded by this run alone.
    """

    def __init__(self, client, work_dir: Path | str, max_per_file: int = 50_000, max_bytes: int = 150_000_000,
                max_tokens_per_file: int = 2_000_000, poll_seconds: float = 60,
                record: Callable[..., None] = lambda *a: None,
                mark_done: Callable[[str, str], None] = lambda *a: None,
                sleep: Callable[[float], None] = time.sleep,
                before_submit: Callable[[float], None] = lambda usd: None):
        self._client = client
        self._dir = Path(work_dir)
        self._max = max_per_file
        self._max_bytes = max_bytes
        self._max_tokens = max_tokens_per_file
        self._poll = poll_seconds
        self._record = record
        self._mark_done = mark_done
        self._sleep = sleep
        self._before_submit = before_submit
        self._batch_status: dict[str, str] = {}
        self._expected_ids: dict[str, set[str]] = {}

    def _submit(self, lines: list[dict], kind: str, endpoint: str, index: int, estimated_usd: float) -> str:
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / f"{kind}-{index}-{uuid.uuid4().hex}.jsonl"
        path.write_text("\n".join(json.dumps(line, ensure_ascii=False) for line in lines), encoding="utf-8")
        with path.open("rb") as handle:
            uploaded = self._client.files.create(file=handle, purpose="batch")
        batch = self._client.batches.create(input_file_id=uploaded.id, endpoint=endpoint, completion_window="24h")
        self._expected_ids[batch.id] = {line["custom_id"] for line in lines}
        with (self._dir / "submitted.log").open("a", encoding="utf-8") as handle:
            handle.write(f"{batch.id} {kind} {path}\n")
        try:
            self._record(batch.id, kind, endpoint, len(lines), str(path), estimated_usd)
        except Exception:
            log.error("record() failed for batch %s (kind=%s); the batch was already submitted to OpenAI "
                     "and needs to be tracked manually", batch.id, kind)
            raise
        log.info("submitted %s batch %s with %d requests", kind, batch.id, len(lines))
        return batch.id

    def fetch(self, batch_id: str) -> list[str]:
        """Wait for one batch and return its raw result lines (successes and errors) WITHOUT marking
        it done. A caller that commits results in blocks calls `done(batch_id)` after its last commit."""
        while True:
            try:
                batch = self._client.batches.retrieve(batch_id)
            except (APIConnectionError, APITimeoutError) as exc:
                log.warning("network error polling batch %s (%s); retrying after %ss", batch_id, exc, self._poll)
                self._sleep(self._poll)
                continue
            if batch.status in TERMINAL:
                break
            self._sleep(self._poll)
        self._batch_status[batch_id] = batch.status
        if batch.status in NON_SUCCESS_STATUSES:
            log.error("batch %s ended %s: %s", batch_id, batch.status, getattr(batch, "errors", None))
        lines: list[str] = []
        for file_id in (batch.output_file_id, getattr(batch, "error_file_id", None)):
            if file_id:
                lines.extend(line for line in self._client.files.content(file_id).text.splitlines() if line.strip())
        return lines

    def done(self, batch_id: str) -> None:
        """Mark a fetched batch done (A3): it no longer counts as in flight for `ensure_within`."""
        self._mark_done(batch_id, self._batch_status.get(batch_id, "unknown"))

    def collect(self, batch_id: str) -> Iterator[str]:
        """Wait for one batch and yield its raw result lines (successes and errors), then mark
        it done (A3) so a later `ensure_within` no longer counts it as in flight. See the class
        docstring for the commit-before-advancing contract this implies for callers."""
        yield from self.fetch(batch_id)
        self.done(batch_id)

    def file_budget(self) -> FileBudget:
        return FileBudget(self._max, self._max_bytes, self._max_tokens * BATCH_TOKEN_HEADROOM)

    def _group_lines(self, lines: Sequence[dict]) -> list[list[dict]]:
        """A4 plus the enqueued-token-limit fix: a new file starts when adding a line would pass
        `max_bytes`, `max_per_file`, or `max_tokens_per_file` (less BATCH_TOKEN_HEADROOM)."""
        groups: list[list[dict]] = []
        current: list[dict] = []
        budget = self.file_budget()
        for line in lines:
            if not budget.admit(line):
                groups.append(current)
                current, budget = [], self.file_budget()
                budget.admit(line)
            current.append(line)
        if current:
            groups.append(current)
        return groups

    def outcomes(self, batch_id: str, lines: Sequence[str], expected_ids: Sequence[str]) -> list[LlmOutcome]:
        """A fetched batch's outcomes, plus an error outcome for every expected id it did not return."""
        parsed = [parse_batch_line(line) for line in lines]
        missing = set(expected_ids) - {o.custom_id for o in parsed}
        status = self._batch_status.get(batch_id, "unknown")
        return parsed + [LlmOutcome(custom_id, None, 0, 0, error=f"no result: batch {batch_id} {status}")
                         for custom_id in sorted(missing)]

    def submit_file(self, lines: list[dict], kind: str, endpoint: str, index: int, estimated_usd: float) -> str:
        """Check the cap (`before_submit`, raises to stop), then submit one file that fits the limits."""
        self._before_submit(estimated_usd)
        return self._submit(lines, kind, endpoint, index, estimated_usd)

    def _collect_group(self, batch_id: str, expected_ids: Sequence[str]) -> Iterator[LlmOutcome]:
        yield from self.outcomes(batch_id, self.fetch(batch_id), list(expected_ids))
        self.done(batch_id)

    def resume(self, batch_ids: Sequence[str]) -> Iterator[LlmOutcome]:
        """Re-attach to batches already submitted (by this run or a prior, interrupted one). When
        the batch's input file was written by this runner instance, missing custom ids (e.g. from
        a batch that failed validation before producing any output) are reported as error outcomes;
        otherwise this just logs, since there is no local record of which ids were expected."""
        for batch_id in batch_ids:
            expected = self._expected_ids.get(batch_id)
            if expected is not None:
                yield from self._collect_group(batch_id, expected)
                continue
            got_any = False
            for line in self.collect(batch_id):
                got_any = True
                yield parse_batch_line(line)
            if not got_any:
                log.warning("batch %s returned no results and its input file is not known to this runner; "
                           "cannot report which custom ids are missing", batch_id)

    def submit_sequentially(self, lines: Sequence[dict], kind: str, endpoint: str,
                            estimated_usd: float = 0.0) -> Iterator[tuple[str, list[dict]]]:
        """Submit one file at a time, yielding (batch_id, its lines). The next file is submitted only
        when the caller asks for it, i.e. after it has collected the previous one, so this run never
        has more than one file's worth of tokens enqueued against the org's per-model limit."""
        groups = self._group_lines(lines)
        total = len(lines)
        for index, group in enumerate(groups):
            estimate = estimated_usd * (len(group) / total) if total else 0.0
            # Raises to stop: later files are checked against the spend the earlier ones actually recorded.
            yield self.submit_file(group, kind, endpoint, index, estimate), group

    def run(self, tasks: Sequence[LlmTask], kind: str, estimated_usd: float = 0.0) -> Iterator[LlmOutcome]:
        """Submit and collect one file at a time (see `submit_sequentially`)."""
        lines = [chat_line(t) for t in tasks]
        for batch_id, group in self.submit_sequentially(lines, kind, CHAT_ENDPOINT, estimated_usd):
            yield from self._collect_group(batch_id, (line["custom_id"] for line in group))
