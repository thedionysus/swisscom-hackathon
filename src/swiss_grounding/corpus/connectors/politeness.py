"""Per-host request spacing shared by every corpus connector, across threads, plus the 429/503
backoff every connector's HTTP requests go through.

Two sources crawled in parallel can share a host (or a source can fetch pages and then PDFs from
the same host); the crawl delay is a promise to that host, so it is enforced per host, not per
connector instance. Request starts on one host are spaced at least `delay` seconds apart.
"""
import email.utils
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

DEFAULT_RETRY_SECONDS = 30.0
MAX_RETRY_SECONDS = 120.0
MAX_HOST_DELAY_SECONDS = 30.0
RETRY_ATTEMPTS = 3
_BACKOFF_STATUSES = frozenset({429, 503})
# Transport failures worth another attempt: the connection could not be made, or the server dropped
# it (www.gerichte-zh.ch, 2 of 3 attempts on 2026-09-23). A read timeout is not retried: a server too
# slow to answer once would hold the crawl for three timeouts.
_RETRY_TRANSPORT_ERRORS = (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError, httpx.ReadError)
TRANSPORT_RETRY_SECONDS = 2.0


class HostThrottle:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._guard = threading.Lock()
        self._locks: dict[str, threading.Lock] = {}
        self._last: dict[str, float] = {}
        self._last_delay: dict[str, float] = {}
        self._min_delay: dict[str, float] = {}

    def _host_lock(self, host: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(host, threading.Lock())

    def wait(self, url: str, delay: float, sleep: Callable[[float], None] = time.sleep) -> None:
        """Block until a request to `url`'s host may start, then claim that slot.

        The host lock is held while sleeping, so concurrent callers for one host queue up
        behind each other and each gets its own slot. `delay` is raised to this host's own
        minimum when `backoff` has bumped it (see below), so every caller -- not only the one
        that hit the 429 -- respects it for the rest of the run.
        """
        host = urlparse(url).netloc.lower()
        delay = max(delay, self._min_delay.get(host, 0.0))
        if delay > 0:
            with self._guard:
                self._last_delay[host] = delay
        if delay <= 0:
            return
        with self._host_lock(host):
            last = self._last.get(host)
            if last is not None:
                remaining = last + delay - self._clock()
                if remaining > 0:
                    sleep(remaining)
            self._last[host] = self._clock()

    def require(self, url: str, delay: float) -> None:
        """Make `delay` a floor for every later request to `url`'s host, whichever connector sends
        it: a robots.txt Crawl-delay read while crawling pages also binds that host's PDF downloads.
        Never lowers a floor `backoff` has already raised."""
        host = urlparse(url).netloc.lower()
        with self._guard:
            self._min_delay[host] = max(self._min_delay.get(host, 0.0), delay)

    def backoff(self, url: str, retry_after: float, sleep: Callable[[float], None] = time.sleep) -> None:
        """After a 429/503: sleep `retry_after` seconds via this host's own slot (so every other
        thread waiting on the same host queues up behind it too), then raise the host's minimum
        delay to at least double what it last was (never less than 2s), capped at
        MAX_HOST_DELAY_SECONDS, for the rest of the run.
        """
        host = urlparse(url).netloc.lower()
        with self._host_lock(host):
            if retry_after > 0:
                sleep(retry_after)
            self._last[host] = self._clock()
        with self._guard:
            base = self._last_delay.get(host, 1.0)
            raised = min(max(base * 2, 2.0), MAX_HOST_DELAY_SECONDS)
            self._min_delay[host] = max(self._min_delay.get(host, 0.0), raised)


SHARED_THROTTLE = HostThrottle()


def parse_retry_after(value: str | None) -> float:
    """Seconds a Retry-After header asks us to wait (RFC 9110): digits are seconds, anything else
    is tried as an HTTP-date. Missing or unparseable values default to DEFAULT_RETRY_SECONDS;
    every result is capped at MAX_RETRY_SECONDS and never negative.
    """
    if not value:
        return DEFAULT_RETRY_SECONDS
    value = value.strip()
    if value.isdigit():
        return min(float(value), MAX_RETRY_SECONDS)
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return DEFAULT_RETRY_SECONDS
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return min(max((when - datetime.now(UTC)).total_seconds(), 0.0), MAX_RETRY_SECONDS)


@dataclass(frozen=True)
class FetchResult:
    """A response reduced to what `request_with_backoff` needs to see, plus whatever body the
    caller already read off the wire (empty when the response was never read, e.g. a 429)."""
    status_code: int
    headers: Mapping[str, str]
    body: bytes = b""


def request_with_backoff(url: str, throttle: HostThrottle, before: Callable[[str], None],
                         send: Callable[[], Any], sleep: Callable[[float], None] = time.sleep,
                         attempts: int = RETRY_ATTEMPTS) -> Any:
    """Call `send()` up to `attempts` times total, backing off on 429/503 per RFC 9110.

    `before(url)` is the caller's normal per-host politeness wait; it runs before every attempt,
    including retries, so a host delay `backoff` just raised applies to the retry too. `send()`'s
    result needs only `.status_code` and `.headers` -- an httpx.Response or a `FetchResult` both
    qualify. On 429/503, sleeps for Retry-After via the host's own throttle slot (so every thread
    on that host waits) and raises the host's delay for the rest of the run, then retries. The
    last response is returned once attempts run out or a non-429/503 status comes back.
    A dropped or refused connection is retried the same way, after TRANSPORT_RETRY_SECONDS times the
    attempt number; the last attempt's exception propagates.
    """
    result = None
    for attempt in range(1, attempts + 1):
        before(url)
        try:
            result = send()
        except _RETRY_TRANSPORT_ERRORS:
            if attempt == attempts:
                raise
            throttle.backoff(url, TRANSPORT_RETRY_SECONDS * attempt, sleep)
            continue
        if result.status_code not in _BACKOFF_STATUSES or attempt == attempts:
            return result
        throttle.backoff(url, parse_retry_after(result.headers.get("retry-after")), sleep)
    return result
