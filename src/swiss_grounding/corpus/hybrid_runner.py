"""Batch API and direct calls working through one task list at the same time.

At OpenAI's low usage tiers the Batch queue limit (2M enqueued tokens for gpt-5-nano at Tier 1) caps how
much work can wait at once, so batches alone run one ~1,300-chunk file every several minutes. Direct calls
are limited separately (tokens per minute), so running both roughly doubles throughput. Direct calls cost
twice the batch price; each outcome carries `sync` so ingestion prices it by its own path.

Both paths take tasks from one shared pool, so no task is sent twice. Outcomes are handed to the caller
on its own thread, one at a time, because the run_* functions commit each outcome before asking for the
next; a batch is marked done only once its last outcome has been handed over (as BatchRunner requires).
"""
import queue
import threading
from collections import deque
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass

from swiss_grounding.corpus.runner import (
    CHAT_ENDPOINT,
    BatchRunner,
    LlmOutcome,
    LlmTask,
    chat_line,
    complete_one,
)


class _TaskPool:
    """Thread-safe queue of tasks both paths draw from. `close()` stops handing out work."""

    def __init__(self, tasks: Sequence[LlmTask]):
        self._tasks = deque(tasks)
        self._lock = threading.Lock()

    def take_one(self) -> LlmTask | None:
        with self._lock:
            return self._tasks.popleft() if self._tasks else None

    def take_while(self, admit: Callable[[LlmTask], bool]) -> list[LlmTask]:
        with self._lock:
            taken = []
            while self._tasks and admit(self._tasks[0]):
                taken.append(self._tasks.popleft())
            return taken

    def close(self) -> None:
        with self._lock:
            self._tasks.clear()


@dataclass(frozen=True)
class _BatchDone:
    batch_id: str


@dataclass(frozen=True)
class _Failed:
    error: BaseException


_FINISHED = object()


class HybridRunner:
    def __init__(self, batch_runner: BatchRunner, llm, workers: int):
        self._batch = batch_runner
        self._llm = llm
        self._workers = workers

    def run(self, tasks: Sequence[LlmTask], kind: str, estimated_usd: float = 0.0) -> Iterator[LlmOutcome]:
        pool = _TaskPool(tasks)
        results: queue.Queue = queue.Queue()
        usd_per_task = estimated_usd / len(tasks) if tasks else 0.0
        producers = [threading.Thread(target=self._batch_side, args=(pool, results, kind, usd_per_task),
                                      daemon=True)]
        producers += [threading.Thread(target=self._direct_side, args=(pool, results), daemon=True)
                      for _ in range(self._workers)]
        for thread in producers:
            thread.start()
        try:
            yield from self._hand_over(results, len(producers))
        finally:
            pool.close()

    def _hand_over(self, results: queue.Queue, producers: int) -> Iterator[LlmOutcome]:
        finished = 0
        while finished < producers:
            item = results.get()
            if item is _FINISHED:
                finished += 1
            elif isinstance(item, _BatchDone):
                self._batch.done(item.batch_id)     # every outcome of it was yielded (and so committed)
            elif isinstance(item, _Failed):
                raise item.error
            else:
                yield item

    def _batch_side(self, pool: _TaskPool, results: queue.Queue, kind: str, usd_per_task: float) -> None:
        try:
            index = 0
            while group := self._take_file(pool):
                lines = [chat_line(task) for task in group]
                batch_id = self._batch.submit_file(lines, kind, CHAT_ENDPOINT, index, usd_per_task * len(group))
                for outcome in self._batch.outcomes(batch_id, self._batch.fetch(batch_id),
                                                    [task.custom_id for task in group]):
                    results.put(outcome)
                results.put(_BatchDone(batch_id))
                index += 1
        except BaseException as exc:  # noqa: BLE001 - re-raised on the caller's thread
            pool.close()
            results.put(_Failed(exc))
        finally:
            results.put(_FINISHED)

    def _take_file(self, pool: _TaskPool) -> list[LlmTask]:
        budget = self._batch.file_budget()
        return pool.take_while(lambda task: budget.admit(chat_line(task)))

    def _direct_side(self, pool: _TaskPool, results: queue.Queue) -> None:
        try:
            while task := pool.take_one():
                results.put(complete_one(self._llm, task))
        except BaseException as exc:  # noqa: BLE001 - re-raised on the caller's thread
            pool.close()
            results.put(_Failed(exc))
        finally:
            results.put(_FINISHED)
