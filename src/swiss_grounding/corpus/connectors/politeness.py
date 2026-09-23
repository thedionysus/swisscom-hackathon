"""Per-host request spacing shared by every corpus connector, across threads.

Two sources crawled in parallel can share a host (or a source can fetch pages and then PDFs from
the same host); the crawl delay is a promise to that host, so it is enforced per host, not per
connector instance. Request starts on one host are spaced at least `delay` seconds apart.
"""
import threading
import time
from collections.abc import Callable
from urllib.parse import urlparse


class HostThrottle:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._guard = threading.Lock()
        self._locks: dict[str, threading.Lock] = {}
        self._last: dict[str, float] = {}

    def _host_lock(self, host: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(host, threading.Lock())

    def wait(self, url: str, delay: float, sleep: Callable[[float], None] = time.sleep) -> None:
        """Block until a request to `url`'s host may start, then claim that slot.

        The host lock is held while sleeping, so concurrent callers for one host queue up
        behind each other and each gets its own slot.
        """
        if delay <= 0:
            return
        host = urlparse(url).netloc.lower()
        with self._host_lock(host):
            last = self._last.get(host)
            if last is not None:
                remaining = last + delay - self._clock()
                if remaining > 0:
                    sleep(remaining)
            self._last[host] = self._clock()


SHARED_THROTTLE = HostThrottle()
